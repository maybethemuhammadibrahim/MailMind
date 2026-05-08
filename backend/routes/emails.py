# backend/routes/emails.py
# ---------------------------------------------------------------
# Fetches emails from Gmail using the Gmail REST API v1. Handles
# credential loading/refresh, message listing, body decoding, and
# sender parsing. Also exposes check/mark endpoints for the SQLite
# deduplication layer used by the AI pipeline in Phase 3.
# ---------------------------------------------------------------

import base64
import json
import os
import time
from datetime import datetime
from typing import Optional

from db.sqlite import is_processed, mark_processed
from fastapi import APIRouter
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

router = APIRouter()

# Shared path to the OAuth token file written by auth.py after login
TOKEN_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
)


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _load_credentials():
    """
    Reads token.json and returns a valid Credentials object.
    If the access_token is expired (lifetime ~1 hour), automatically
    refreshes it using the refresh_token and saves the new value.

    Returns:
        Credentials: valid, possibly freshly-refreshed credentials

    Raises:
        FileNotFoundError: if token.json doesn't exist (user never logged in)
        RuntimeError: if token refresh fails
    """
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(
            "token.json not found. Please visit /api/auth/login to connect Gmail."
        )

    with open(TOKEN_PATH, "r") as f:
        data = json.load(f)

    # Reconstruct the Credentials object from the saved dict fields
    creds = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data.get("scopes"),
    )

    # access_token expires every ~1 hour. Use the refresh_token to get a new
    # one automatically — this happens in the background without user input.
    if creds.expired and creds.refresh_token:
        print("[GMAIL] Access token expired — refreshing automatically...")
        creds.refresh(Request())
        data["token"] = creds.token  # update only the short-lived field
        with open(TOKEN_PATH, "w") as f:
            json.dump(data, f, indent=2)
        print("[GMAIL] Token refreshed and saved.")

    return creds


def _build_gmail_service():
    """
    Builds an authenticated Gmail API v1 service client.
    Returns None (instead of raising) so callers can return a clean error dict.

    The 'build' call does NOT make any network request on its own —
    it just creates a resource object used to call API methods.

    Returns:
        Resource | None: Gmail service client, or None on auth failure
    """
    try:
        creds = _load_credentials()
        return build("gmail", "v1", credentials=creds)
    except FileNotFoundError as e:
        print(f"[GMAIL] {e}")
        return None
    except Exception as e:
        print(f"[GMAIL] Failed to build Gmail service: {e}")
        return None


# ---------------------------------------------------------------------------
# Gmail API helpers
# ---------------------------------------------------------------------------


def _list_messages(service, query: str, max_results: int = 50) -> list:  # type: ignore[type-arg]
    """
    Calls messages.list() with a Gmail search query. Retries once on failure
    (waits 2 seconds between attempts) to handle transient network errors.

    Gmail queries work the same as the Gmail search box:
      - 'is:unread'         — only unread emails
      - 'newer_than:1d'     — from the last 24 hours
      - Combined: 'is:unread newer_than:1d'

    Args:
        service    : authenticated Gmail service client
        query      : Gmail search string
        max_results: cap on number of message refs returned (default 50)

    Returns:
        list[dict]: list of {"id": ..., "threadId": ...} message refs
    """
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
    return []  # unreachable but satisfies type checker


def _decode_body(payload: dict) -> str:  # type: ignore[type-arg]
    """
    Recursively decodes the plain-text body from a Gmail message payload.

    Gmail stores message bodies base64url-encoded. Multi-part messages
    (HTML + plain text) are stored as nested 'parts' arrays. We prefer
    the text/plain part so the AI pipeline doesn't have to parse HTML.

    Args:
        payload (dict): the 'payload' key from a Gmail messages.get() response

    Returns:
        str: decoded plain-text body, or empty string if none found
    """
    # Case 1: simple message — body data lives directly on the payload
    raw = payload.get("body", {}).get("data", "")
    if raw:
        return base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")

    # Case 2: multi-part message — iterate over parts
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            raw = part.get("body", {}).get("data", "")
            if raw:
                return base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")
        # Case 3: nested multi-part (e.g. multipart/alternative inside multipart/mixed)
        nested = _decode_body(part)
        if nested:
            return nested

    return ""


def _parse_sender(from_header: str) -> tuple:  # type: ignore[type-arg]
    """
    Splits a raw 'From' header into a display name and email address.

    Handles all common formats:
      'John Doe <john@example.com>'  → ('John Doe', 'john@example.com')
      '<john@example.com>'           → ('john@example.com', 'john@example.com')
      'john@example.com'             → ('john@example.com', 'john@example.com')

    Args:
        from_header (str): raw value of the 'From' header

    Returns:
        tuple[str, str]: (display_name, email_address)
    """
    if "<" in from_header and ">" in from_header:
        name = from_header.split("<")[0].strip().strip('"').strip("'")
        email = from_header.split("<")[1].split(">")[0].strip()
        return (name or email, email)
    addr = from_header.strip()
    return (addr, addr)


def _fetch_full_message(service, message_id: str) -> Optional[dict]:  # type: ignore[type-arg]
    """
    Fetches a single Gmail message with full headers and body text.
    Uses format='full' which returns everything in one request (no extra calls).

    Args:
        service   : authenticated Gmail service
        message_id: the Gmail message ID string

    Returns:
        dict | None: structured email dict, or None if the fetch failed
    """
    try:
        # format='full' returns payload (headers + body parts) + metadata
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        payload = msg.get("payload", {})

        # Gmail returns headers as a list of {name, value} dicts.
        # We convert to a plain dict for easy access.
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        sender_name, sender_email = _parse_sender(headers.get("From", ""))

        # internalDate is Unix timestamp in milliseconds (not seconds!)
        ts_ms = int(msg.get("internalDate", 0))
        timestamp = datetime.fromtimestamp(ts_ms / 1000).isoformat()

        return {
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "sender": sender_name,
            "sender_email": sender_email,
            # Cap body at 3000 chars — enough context for the AI pipeline
            # without hitting token limits in Phase 3
            "body_plain": _decode_body(payload)[:3000],
            "thread_id": msg.get("threadId", ""),
            "timestamp": timestamp,
        }
    except Exception as e:
        print(f"[GMAIL] Failed to fetch message {message_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@router.get("/unread")
def get_unread_emails():
    """
    Fetches up to 50 unread emails received in the last 24 hours.

    Gmail search query used: 'is:unread newer_than:1d'
    (same as typing that in the Gmail search box)

    Emails already recorded in the processed_emails SQLite table are
    silently skipped — this prevents re-running the AI pipeline on
    emails that have already been classified/summarized.

    Returns:
        list[dict]: list of email dicts, each with keys:
                    id, subject, sender, sender_email, body_plain,
                    thread_id, timestamp
        dict: error dict if Gmail is not connected or the API call fails
    """
    service = _build_gmail_service()
    if not service:
        return {
            "error": "Gmail not connected.",
            "hint": "Visit /api/auth/login to connect your Gmail account.",
        }

    try:
        refs = _list_messages(service, query="is:unread newer_than:1d")
        print(f"[GMAIL] Gmail returned {len(refs)} unread message refs.")
    except Exception as e:
        return {"error": f"Failed to list messages from Gmail: {str(e)}"}

    emails = []
    for ref in refs:
        # Skip emails the pipeline has already processed (deduplication)
        if is_processed(ref["id"]):
            print(f"[GMAIL] Skipping already-processed message: {ref['id']}")
            continue

        data = _fetch_full_message(service, ref["id"])
        if data:
            emails.append(data)

    print(f"[GMAIL] Returning {len(emails)} new unread emails to caller.")
    return emails


@router.get("/check/{email_id}")
def check_processed(email_id: str):
    """
    Checks whether a Gmail message has already been through the AI pipeline.
    Primarily used by n8n workflows to avoid duplicate processing.

    Args:
        email_id (str): the Gmail message ID (e.g. '18f5a2b3c4d5e6f7')

    Returns:
        dict: {"email_id": str, "processed": bool}
    """
    try:
        processed = is_processed(email_id)
        return {"email_id": email_id, "processed": processed}
    except Exception as e:
        print(f"[EMAILS] check_processed error for {email_id}: {e}")
        return {"error": str(e)}


@router.post("/mark-processed")
def mark_email_processed(email_id: str, subject: str = "", sender: str = ""):
    """
    Records an email as processed in SQLite after the AI pipeline finishes.
    Called by Phase 3 pipeline endpoints once classification is done.

    The category and priority_score are set to placeholder values here
    because the real values come from the classifier in Phase 3.

    Args:
        email_id (str): Gmail message ID
        subject  (str): email subject line (stored for reference)
        sender   (str): sender's email address

    Returns:
        dict: {"success": True, "email_id": str} or error dict
    """
    try:
        mark_processed(
            email_id=email_id,
            subject=subject,
            sender=sender,
            category="pending",  # updated by classifier in Phase 3
            priority_score=0,  # updated by classifier in Phase 3
        )
        print(f"[EMAILS] Marked {email_id} as processed in SQLite.")
        return {"success": True, "email_id": email_id}
    except Exception as e:
        print(f"[EMAILS] mark_processed error for {email_id}: {e}")
        return {"error": str(e)}
