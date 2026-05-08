# backend/routes/analytics.py
# ---------------------------------------------------------------
# Endpoints for computing email analytics and security stats.
# /summary powers the dashboard quick-stats bar (Phase 3).
# Full chart data (Phase 6) is provided by /overview + /security.
# ---------------------------------------------------------------

from db.sqlite import get_connection
from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
def get_summary():
    """
    Returns quick aggregate stats from the processed_emails table.
    Used by the home dashboard to show totals at a glance.

    Returns:
        dict: total_processed, categories (breakdown dict),
              spam_blocked, requires_reply_count, top_action_items
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

        # How many need a reply
        cur.execute(
            "SELECT COUNT(*) FROM processed_emails WHERE category IN ('urgent','action-required','meeting-request')"
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


@router.get("/overview")
def get_overview():
    """
    Full analytics overview endpoint — Phase 6 implementation.
    Returns:
        dict: placeholder
    """
    return {"message": "Analytics overview — Phase 6"}


@router.get("/security")
def get_security():
    """
    Security analytics endpoint — Phase 6 implementation.
    Returns:
        dict: placeholder
    """
    return {"message": "Security analytics — Phase 6"}
