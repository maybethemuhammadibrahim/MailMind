# backend/routes/auth.py
# ---------------------------------------------------------------
# Handles Gmail OAuth2 authentication. GET /login redirects the
# user to Google's consent screen; GET /callback exchanges the
# auth code for tokens and saves them to token.json so the Gmail
# API can be used without re-authentication each time.
# ---------------------------------------------------------------

import json
import os
from typing import Optional

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

router = APIRouter()

# --- Gmail OAuth Scopes ---
# Scopes declare exactly what we want access to. Google shows
# these on the consent screen so users know what they're granting.
#   readonly  — read email content, subjects, senders
#   modify    — mark emails as read / change labels (NOT delete)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

# token.json lives at the project root (one level above backend/)
# so it persists across server restarts and isn't inside the package.
TOKEN_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
)


def _build_flow():
    """
    Creates a Google OAuth2 Flow object from our app's credentials.
    The Flow class manages URL generation and the token exchange POST.

    We pass the credentials as a dict instead of a file so we can
    load them dynamically from environment variables via config.py.

    Returns:
        Flow: configured OAuth2 flow ready to generate URLs or fetch tokens
    """
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
    """
    Shows exactly what REDIRECT_URI and CLIENT_ID the app is using right now.
    Compare the redirect_uri shown here against your Google Cloud Console entry.
    They must be byte-for-byte identical.

    Returns:
        dict: the live config values loaded from .env
    """
    return {
        "redirect_uri": REDIRECT_URI,
        "client_id": GOOGLE_CLIENT_ID[:20] + "..." if GOOGLE_CLIENT_ID else "NOT SET",
        "client_secret_set": bool(GOOGLE_CLIENT_SECRET),
        "hint": "Copy the exact redirect_uri value above into Google Cloud Console → Credentials → Authorized redirect URIs",
    }


@router.get("/login")
def login():
    """
    Step 1 of the OAuth2 flow — send the user to Google's consent screen.

    How OAuth2 works (simplified):
      1. We redirect the user to Google with our client_id + requested scopes.
      2. Google shows: 'MailMind wants to read your Gmail. Allow?'
      3. User clicks Allow → Google redirects to /callback with a one-time code.

    access_type='offline' tells Google to include a refresh_token alongside
    the access_token. The refresh_token never expires (unless revoked), so
    the app can silently get new access_tokens every hour without bothering
    the user to log in again.

    prompt='consent' forces the consent screen every time, which ensures
    Google always returns a fresh refresh_token (it won't on repeat logins
    without this flag).

    Returns:
        RedirectResponse: sends the browser to Google's OAuth consent page
    """
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
    """
    Step 2 of OAuth2 — Google redirects here after the user grants access.

    Google sends a one-time 'code' (authorization code) in the URL. We
    POST that code to Google's token endpoint to exchange it for real tokens:
      - access_token  : short-lived (~1 hour), sent with every API request
      - refresh_token : long-lived, used to get new access_tokens silently

    Both tokens are saved to token.json at the project root so the emails
    module can load them on each request without re-authenticating.

    Args:
        code  (str): one-time authorization code from Google
        error (str): set if the user clicked 'Deny' on the consent screen
        state (str): optional CSRF state param (not used yet)

    Returns:
        RedirectResponse: to /settings?auth=success on success
        dict: error message if something goes wrong
    """
    if error:
        print(f"[AUTH] OAuth error returned by Google: {error}")
        return {"error": f"Google denied access: {error}"}

    if not code:
        return {
            "error": "No authorization code received. Please try /api/auth/login again."
        }

    try:
        flow = _build_flow()

        # This makes a POST to https://oauth2.googleapis.com/token
        # and exchanges the one-time code for access + refresh tokens.
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Serialize credentials to a plain dict so we can store as JSON.
        # We need all fields to reconstruct the Credentials object later.
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
        # Redirect back to the settings page with a success flag
        return RedirectResponse(url="/settings?auth=success")

    except Exception as e:
        print(f"[AUTH] Token exchange failed: {e}")
        return {"error": f"Token exchange failed: {str(e)}"}


@router.get("/status")
def auth_status():
    """
    Checks whether the user has a valid Gmail connection.
    Used by the settings page to show 'Connected' or 'Connect Gmail'.

    A token.json file present means the user completed OAuth at some point.
    The actual token validity is checked (and refreshed if needed) when
    emails are fetched.

    Returns:
        dict: {"connected": bool} plus a hint if not connected
    """
    if os.path.exists(TOKEN_PATH):
        print("[AUTH] Gmail connected — token.json exists.")
        return {"connected": True}

    print("[AUTH] Gmail not connected — token.json missing.")
    return {
        "connected": False,
        "hint": "Visit /api/auth/login to connect your Gmail account.",
    }


@router.get("/logout")
def logout():
    """
    Disconnects Gmail by deleting the saved token.json file.
    After this, the user must go through /api/auth/login again.

    Returns:
        dict: confirmation message
    """
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        print("[AUTH] token.json deleted — user logged out.")
        return {"success": True, "message": "Gmail disconnected successfully."}

    return {"success": False, "message": "No active Gmail connection found."}
