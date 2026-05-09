# backend/routes/analytics.py
# ---------------------------------------------------------------
# FastAPI router for email analytics and security statistics.
# /summary powers the Phase 3 dashboard quick-stats bar.
# /overview and /security (Phase 6) provide full chart-ready data
# computed entirely from the processed_emails SQLite table.
# ---------------------------------------------------------------

from db.sqlite import get_analytics_overview, get_analytics_security, get_connection
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response models — make the API self-documenting at /docs
# ---------------------------------------------------------------------------


class HourlyEntry(BaseModel):
    """A single hour-bucket for the volume timeline."""

    hour: str    # human-readable label, e.g. '8am', '3pm', '12am'
    count: int   # number of emails processed in that hour


class OverviewResponse(BaseModel):
    """
    Full analytics overview payload returned by GET /api/analytics/overview.

    Fields:
        total_today       — emails processed today
        spam_count        — emails flagged is_spam=1
        flagged_suspicious— emails categorised 'spam' but not flagged is_spam
        by_category       — count per AI-assigned category label
        by_sender_domain  — top 5 sender domains + 'other' bucket
        hourly_volume     — per-hour email count for today
    """

    total_today: int
    spam_count: int
    flagged_suspicious: int
    by_category: dict
    by_sender_domain: dict
    hourly_volume: list[HourlyEntry]


class SuspiciousSender(BaseModel):
    """One entry in the suspicious-senders list."""

    email: str    # the raw sender address
    reason: str   # human-readable explanation of why it is suspicious


class SecurityResponse(BaseModel):
    """
    Security analytics payload returned by GET /api/analytics/security.

    Fields:
        spam_rate_percent  — percentage of all processed emails that are spam
        suspicious_senders — list of flagged sender addresses with reasons
        safe_percent       — 100 - spam_rate_percent
    """

    spam_rate_percent: float
    suspicious_senders: list[SuspiciousSender]
    safe_percent: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/summary")
def get_summary():
    """
    Returns quick aggregate stats from the processed_emails table.
    Used by the home dashboard to show totals at a glance (Phase 3).

    Returns:
        dict: total_processed, categories (breakdown dict),
              spam_blocked, requires_reply_count
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Total emails run through the pipeline
        cur.execute("SELECT COUNT(*) FROM processed_emails")
        total = cur.fetchone()[0]

        # Breakdown per category
        cur.execute(
            "SELECT category, COUNT(*) as n FROM processed_emails GROUP BY category ORDER BY n DESC"
        )
        categories = {row["category"]: row["n"] for row in cur.fetchall()}

        # How many are spam
        cur.execute("SELECT COUNT(*) FROM processed_emails WHERE is_spam = 1")
        spam = cur.fetchone()[0]

        # How many need a reply — urgent/action-required/meeting-request categories
        cur.execute(
            "SELECT COUNT(*) FROM processed_emails "
            "WHERE category IN ('urgent','action-required','meeting-request')"
        )
        needs_reply = cur.fetchone()[0]

        conn.close()
        print(
            f"[Analytics] Summary — total={total}, spam={spam}, needs_reply={needs_reply}"
        )
        return {
            "total_processed": total,
            "categories": categories,
            "spam_blocked": spam,
            "requires_reply_count": needs_reply,
        }
    except Exception as exc:
        print(f"[Analytics] Summary failed: {exc}")
        return {
            "total_processed": 0,
            "categories": {},
            "spam_blocked": 0,
            "requires_reply_count": 0,
        }


@router.get("/overview", response_model=OverviewResponse)
def get_overview():
    """
    Full analytics overview endpoint (Phase 6).

    Delegates all SQL work to get_analytics_overview() in db/sqlite.py,
    which contains detailed comments explaining every calculation.

    Returns:
        OverviewResponse: total_today, spam_count, flagged_suspicious,
                          by_category dict, by_sender_domain dict,
                          hourly_volume list
    """
    print("[Analytics] GET /overview called")

    try:
        data = get_analytics_overview()
        print(
            f"[Analytics] Overview — total_today={data['total_today']}, "
            f"categories={len(data['by_category'])}"
        )
        return data

    except Exception as exc:
        print(f"[Analytics] Overview failed: {exc}")
        # Return a safe empty payload so the frontend doesn't crash
        return {
            "total_today":        0,
            "spam_count":         0,
            "flagged_suspicious": 0,
            "by_category":        {},
            "by_sender_domain":   {},
            "hourly_volume":      [],
        }


@router.get("/security", response_model=SecurityResponse)
def get_security():
    """
    Security analytics endpoint (Phase 6).

    Delegates all SQL work to get_analytics_security() in db/sqlite.py.
    Returns spam rate percentages and a list of suspicious sender addresses
    with human-readable reasons (e.g. 'flagged as spam by AI classifier').

    Returns:
        SecurityResponse: spam_rate_percent, suspicious_senders, safe_percent
    """
    print("[Analytics] GET /security called")

    try:
        data = get_analytics_security()
        print(
            f"[Analytics] Security — spam_rate={data['spam_rate_percent']}%, "
            f"suspicious_senders={len(data['suspicious_senders'])}"
        )
        return data

    except Exception as exc:
        print(f"[Analytics] Security failed: {exc}")
        # Return a safe default so the frontend doesn't crash
        return {
            "spam_rate_percent":  0.0,
            "suspicious_senders": [],
            "safe_percent":       100.0,
        }
