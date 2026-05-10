
import json
import os
from typing import Optional

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

TOKEN_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
)


def _build_flow():
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


@router.get("/debug")
def debug_config():
    return {
        "redirect_uri": REDIRECT_URI,
        "client_id": GOOGLE_CLIENT_ID[:20] + "..." if GOOGLE_CLIENT_ID else "NOT SET",
        "client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "hint": "Copy the exact redirect_uri value above into Google Cloud Console → Credentials → Authorized redirect URIs",
    }


@router.get("/login")
def login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return {
            "error": "Google credentials not configured.",
            "hint": "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file.",
        }

    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    print(f"[AUTH] Redirecting user to Google consent screen...")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def callback(
    code: Optional[str] = None, error: Optional[str] = None, state: Optional[str] = None
):
    if error:
        print(f"[AUTH] OAuth error returned by Google: {error}")
        return {"error": f"Google denied access: {error}"}

    if not code:
        return {
            "error": "No authorization code received. Please try /api/auth/login again."
        }

    try:
        flow = _build_flow()

        flow.fetch_token(code=code)
        creds = flow.credentials

        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else [],
        }

        with open(TOKEN_PATH, "w") as f:
            json.dump(token_data, f, indent=2)

        print(f"[AUTH] Tokens saved successfully to {TOKEN_PATH}")
        return RedirectResponse(url="/settings?auth=success")

    except Exception as e:
        print(f"[AUTH] Token exchange failed: {e}")
        return {"error": f"Token exchange failed: {str(e)}"}


@router.get("/status")
def auth_status():
    if not os.path.exists(TOKEN_PATH):
        print("[AUTH] Gmail not connected — token.json missing.")
        return {
            "connected": False,
            "email": None,
            "hint": "Visit /api/auth/login to connect your Gmail account.",
        }

    print("[AUTH] Gmail connected — token.json exists.")

    email = None
    try:
        with open(TOKEN_PATH, "r") as f:
            token_data = json.load(f)

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )

        # auto refreshes token if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data["token"] = creds.token
            with open(TOKEN_PATH, "w") as f:
                json.dump(token_data, f, indent=2)

        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", None)
        print(f"[AUTH] Gmail profile email: {email}")
    except Exception as exc:
        print(f"[AUTH] Could not fetch Gmail profile: {exc}")

    return {"connected": True, "email": email}


@router.get("/logout")
def logout():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        print("[AUTH] token.json deleted — user logged out.")
        return {"success": True, "message": "Gmail disconnected successfully."}

    return {"success": False, "message": "No active Gmail connection found."}
