# backend/routes/dev.py
# ---------------------------------------------------------------
# Developer-only endpoints used by the /dev sandbox page.
# These routes expose internal state (DB stats, live API checks)
# that would not exist in a production build.
# ---------------------------------------------------------------

import json
import os
import time

from config import AI_MODEL_FAST, DATABASE_PATH, GEMINI_API_KEY
from db.sqlite import get_connection
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Token file location (same path used by auth.py and emails.py)
TOKEN_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
)


# Pydantic model for the AI test request body
class TestAIRequest(BaseModel):
    """Request body for POST /api/dev/test-ai."""

    subject: str = "Test subject"
    sender: str = "test@example.com"
    body: str = "This is a test email body."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
def dev_status():
    """
    Returns the live status of the three main dependencies:
      - Gmail    : token.json exists AND has a refresh_token
      - AI API   : GEMINI_API_KEY is set in .env
      - Database : SQLite file exists at DATABASE_PATH

    Returns:
        dict: {gmail, ai, db} each with {ok, detail}
    """
    # --- Gmail ---
    gmail_ok = False
    gmail_detail = "token.json not found"
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH) as f:
                tok = json.load(f)
            gmail_ok = bool(tok.get("refresh_token"))
            gmail_detail = (
                "Connected" if gmail_ok else "token.json missing refresh_token"
            )
        except Exception as exc:
            gmail_detail = f"token.json unreadable: {exc}"

    # --- AI ---
    ai_ok = bool(GEMINI_API_KEY)
    ai_detail = "API key set" if ai_ok else "GEMINI_API_KEY not set in .env"

    # --- Database ---
    db_path = os.path.abspath(DATABASE_PATH)
    db_ok = os.path.exists(db_path)
    db_detail = db_path if db_ok else f"Not found at {db_path}"

    print(f"[DEV] Status — Gmail:{gmail_ok} AI:{ai_ok} DB:{db_ok}")
    return {
        "gmail": {"ok": gmail_ok, "detail": gmail_detail},
        "ai": {"ok": ai_ok, "detail": ai_detail, "model": AI_MODEL_FAST},
        "db": {"ok": db_ok, "detail": db_detail},
    }


@router.get("/db-stats")
def dev_db_stats():
    """
    Returns row counts for every table in the SQLite database.
    Shows whether the pipeline is storing data correctly.

    Returns:
        dict: {table_name: row_count} for all 5 tables
    """
    tables = ["processed_emails", "todos", "meetings", "orders", "settings"]
    stats = {}
    try:
        conn = get_connection()
        cur = conn.cursor()
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            stats[table] = cur.fetchone()[0]
        conn.close()
        print(f"[DEV] DB stats: {stats}")
    except Exception as exc:
        print(f"[DEV] DB stats error: {exc}")
        return {"error": str(exc)}
    return stats


@router.post("/test-ai")
def dev_test_ai(req: TestAIRequest):
    """
    Sends a test email to Gemini via the native google-genai SDK and
    returns the raw classification JSON. Used by /dev to confirm the
    AI key works end-to-end before Phase 3.

    Args:
        req: TestAIRequest with subject, sender, body

    Returns:
        dict: {ok, result, model, latency_ms} or {ok, error}
    """
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY is not set in your .env file."}

    system = (
        "You are an email classification system. "
        "Return ONLY valid JSON with exactly these keys: "
        "category (one of: urgent, action-required, meeting-request, "
        "order-update, spam, promotions, forum, social_media, updates, verify_code), "
        "priority_score (integer 1-10), "
        "requires_reply (boolean), "
        "is_spam (boolean), "
        "is_order_email (boolean), "
        "action_items (list of strings)."
    )
    prompt = (
        f"Classify this email:\n\n"
        f"Subject: {req.subject}\nFrom: {req.sender}\n\n{req.body[:1000]}"
    )

    # Import here so a missing key doesn't crash the whole module on startup
    from pipeline.gemini import call_fast

    start = time.time()
    try:
        result = call_fast(prompt, system)
        elapsed = int((time.time() - start) * 1000)
        print(f"[DEV] AI test OK — {elapsed}ms")
        return {
            "ok": True,
            "result": result,
            "model": AI_MODEL_FAST,
            "latency_ms": elapsed,
        }
    except Exception as exc:
        print(f"[DEV] AI test failed: {exc}")
        return {"ok": False, "error": str(exc)}


@router.post("/test-hybrid")
def dev_test_hybrid(req: TestAIRequest):
    """
    Runs the full hybrid classification pipeline (sklearn → Gemini)
    and returns both intermediate and final results.

    Returns:
        dict: {
            ok, sklearn_category, gemini_result,
            model, latency_ms
        } or {ok, error}
    """
    from pipeline.classifier import classify_email
    from pipeline.sklearn_classifier import predict_category

    # --- Step 1: sklearn coarse triage ---
    try:
        sklearn_cat = predict_category(req.subject, req.body)
    except RuntimeError as exc:
        sklearn_cat = f"unavailable ({exc})"

    # --- Step 2: Full hybrid pipeline (sklearn + Gemini) ---
    start = time.time()
    try:
        result = classify_email(req.subject, req.sender, req.body)
        elapsed = int((time.time() - start) * 1000)
        print(f"[DEV] Hybrid test OK — sklearn={sklearn_cat}, "
              f"final={result.get('category')} — {elapsed}ms")
        return {
            "ok": True,
            "sklearn_category": sklearn_cat,
            "gemini_result": result,
            "model": AI_MODEL_FAST,
            "latency_ms": elapsed,
        }
    except Exception as exc:
        print(f"[DEV] Hybrid test failed: {exc}")
        return {"ok": False, "sklearn_category": sklearn_cat, "error": str(exc)}


@router.get("/emails")
def dev_fetch_emails():
    """
    Fetches unread emails from Gmail (last 24h) and annotates each
    with an `in_db` flag showing DB coverage at a glance.

    Returns:
        dict: {emails, total, already_in_db}
    """
    from db.sqlite import is_processed
    from routes.emails import _build_gmail_service, _fetch_full_message, _list_messages

    service = _build_gmail_service()
    if not service:
        return {"error": "Gmail not connected. Visit /api/auth/login first."}

    try:
        refs = _list_messages(service, query="is:unread newer_than:1d", max_results=20)
    except Exception as exc:
        return {"error": str(exc)}

    emails = []
    for ref in refs:
        data = _fetch_full_message(service, ref["id"])
        if data:
            data["in_db"] = is_processed(ref["id"])
            emails.append(data)

    already_in_db = sum(1 for e in emails if e["in_db"])
    print(f"[DEV] Fetched {len(emails)} emails, {already_in_db} already in DB")
    return {"emails": emails, "total": len(emails), "already_in_db": already_in_db}
