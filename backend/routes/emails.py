
import base64
import json
import os
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Optional

from db.sqlite import get_recent_emails, is_processed, mark_processed, save_email
from fastapi import APIRouter
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel

router = APIRouter()

class SendEmailRequest(BaseModel):

    to: str
    subject: str
    body: str
    thread_id: str | None = None


TOKEN_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
)


def _load_credentials():
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(
            "token.json not found. Please visit /api/auth/login to connect Gmail."
        )

    with open(TOKEN_PATH, "r") as f:
        data = json.load(f)

    creds = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data.get("scopes"),
    )

    if creds.expired and creds.refresh_token:
        print("[GMAIL] Access token expired — refreshing automatically...")
        creds.refresh(Request())
        data["token"] = creds.token
        with open(TOKEN_PATH, "w") as f:
            json.dump(data, f, indent=2)
        print("[GMAIL] Token refreshed and saved.")

    return creds


def _build_gmail_service():
    try:
        creds = _load_credentials()
        return build("gmail", "v1", credentials=creds)
    except FileNotFoundError as e:
        print(f"[GMAIL] {e}")
        return None
    except Exception as e:
        print(f"[GMAIL] Failed to build Gmail service: {e}")
        return None


def _list_messages(service, query: str, max_results: int = 50) -> list:
    for attempt in range(2):
        try:
            response = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            return response.get("messages", [])
        except Exception as e:
            if attempt == 0:
                print(f"[GMAIL] messages.list() failed: {e}. Retrying in 2s...")
                time.sleep(2)
            else:
                print(f"[GMAIL] messages.list() failed on retry: {e}")
                raise
    return []


def _decode_body(payload: dict) -> str:
    # decodes multipart email body recursively
    raw = payload.get("body", {}).get("data", "")
    if raw:
        return base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            raw = part.get("body", {}).get("data", "")
            if raw:
                return base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")
        nested = _decode_body(part)
        if nested:
            return nested

    return ""


def _parse_sender(from_header: str) -> tuple:
    if "<" in from_header and ">" in from_header:
        name = from_header.split("<")[0].strip().strip('"').strip("'")
        email = from_header.split("<")[1].split(">")[0].strip()
        return (name or email, email)
    addr = from_header.strip()
    return (addr, addr)


def _fetch_full_message(service, message_id: str) -> Optional[dict]:
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        payload = msg.get("payload", {})

        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        sender_name, sender_email = _parse_sender(headers.get("From", ""))

        ts_ms = int(msg.get("internalDate", 0))
        timestamp = datetime.fromtimestamp(ts_ms / 1000).isoformat()

        return {
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "sender": sender_name,
            "sender_email": sender_email,
            "body_plain": _decode_body(payload)[:3000],
            "thread_id": msg.get("threadId", ""),
            "timestamp": timestamp,
            "is_sent": "SENT" in msg.get("labelIds", []),
        }
    except Exception as e:
        print(f"[GMAIL] Failed to fetch message {message_id}: {e}")
        return None


@router.get("/recent")
def get_recent_emails_from_db():
    try:
        return get_recent_emails(limit=30)
    except Exception as e:
        print(f"[EMAILS] Failed to load recent emails from DB: {e}")
        return {"error": f"Failed to load recent emails: {str(e)}"}


@router.post("/sync")
def sync_recent_emails():
    service = _build_gmail_service()
    if not service:
        return {
            "error": "Gmail not connected.",
            "hint": "Visit /api/auth/login to connect your Gmail account.",
        }

    try:
        refs = _list_messages(service, query="newer_than:1d", max_results=30)
        print(f"[GMAIL] Gmail returned {len(refs)} recent message refs.")
    except Exception as e:
        return {"error": f"Failed to list messages from Gmail: {str(e)}"}

    for ref in refs:
        data = _fetch_full_message(service, ref["id"])
        if data:
            save_email(data)

    synced = get_recent_emails(limit=30)
    print(f"[GMAIL] Sync complete. Returning {len(synced)} emails from DB.")
    return synced


@router.get("/check/{email_id}")
def check_processed(email_id: str):
    try:
        processed = is_processed(email_id)
        return {"email_id": email_id, "processed": processed}
    except Exception as e:
        print(f"[EMAILS] check_processed error for {email_id}: {e}")
        return {"error": str(e)}


@router.post("/mark-processed")
def mark_email_processed(email_id: str, subject: str = "", sender: str = ""):
    try:
        mark_processed(
            email_id=email_id,
            subject=subject,
            sender=sender,
            category="pending",
            priority_score=0,
        )
        print(f"[EMAILS] Marked {email_id} as processed in SQLite.")
        return {"success": True, "email_id": email_id}
    except Exception as e:
        print(f"[EMAILS] mark_processed error for {email_id}: {e}")
        return {"error": str(e)}


@router.post("/send")
def send_email(req: SendEmailRequest):
    recipient = req.to.strip()
    subject = req.subject.strip()
    body = req.body.strip()

    if not recipient or not subject or not body:
        return {"error": "to, subject, and body are required."}

    if "," in recipient or ";" in recipient:
        return {"error": "Only one recipient is allowed."}

    _, parsed_email = parseaddr(recipient)
    if not parsed_email or "@" not in parsed_email:
        return {"error": "Invalid recipient email address."}

    service = _build_gmail_service()
    if not service:
        return {
            "error": "Gmail not connected.",
            "hint": "Visit /api/auth/login to connect your Gmail account.",
        }

    try:
        mime = MIMEText(body, _charset="utf-8")
        mime["to"] = parsed_email
        mime["subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")

        payload = {"raw": raw}
        if req.thread_id:
            payload["threadId"] = req.thread_id

        sent = service.users().messages().send(userId="me", body=payload).execute()
        return {
            "success": True,
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
        }
    except Exception as e:
        print(f"[GMAIL] Failed to send email: {e}")
        return {"error": f"Failed to send email: {str(e)}"}


class SaveDraftRequest(BaseModel):

    to: str = ""
    subject: str = ""
    body: str
    thread_id: str | None = None


@router.post("/drafts/save")
def save_gmail_draft(req: SaveDraftRequest):
    body_text = req.body.strip()
    if not body_text:
        return {"error": "body is required and cannot be empty."}

    service = _build_gmail_service()
    if not service:
        return {
            "error": "Gmail not connected.",
            "hint": "Visit /api/auth/login to connect your Gmail account.",
        }

    try:
        mime = MIMEText(body_text, _charset="utf-8")

        if req.to.strip():
            mime["to"] = req.to.strip()
        if req.subject.strip():
            mime["subject"] = req.subject.strip()

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")

        draft_body: dict = {"message": {"raw": raw}}
        if req.thread_id:
            draft_body["message"]["threadId"] = req.thread_id

        result = service.users().drafts().create(
            userId="me", body=draft_body
        ).execute()

        draft_id = result.get("id", "")
        print(f"[GMAIL] Draft saved successfully — draft_id={draft_id}")

        return {"success": True, "draft_id": draft_id}

    except Exception as e:
        print(f"[GMAIL] Failed to save draft: {e}")
        return {"error": f"Failed to save draft: {str(e)}"}
