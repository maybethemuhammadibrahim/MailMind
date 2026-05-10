
from db.sqlite import get_analytics_overview, get_analytics_security, get_connection
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HourlyEntry(BaseModel):

    hour: str
    count: int


class OverviewResponse(BaseModel):

    total_today: int
    spam_count: int
    flagged_suspicious: int
    by_category: dict
    by_sender_domain: dict
    hourly_volume: list[HourlyEntry]


class SuspiciousSender(BaseModel):

    email: str
    reason: str


class SecurityResponse(BaseModel):

    spam_rate_percent: float
    suspicious_senders: list[SuspiciousSender]
    safe_percent: float


@router.get("/summary")
def get_summary():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM processed_emails")
        total = cur.fetchone()[0]

        cur.execute(
            "SELECT category, COUNT(*) as n FROM processed_emails GROUP BY category ORDER BY n DESC"
        )
        categories = {row["category"]: row["n"] for row in cur.fetchall()}

        cur.execute("SELECT COUNT(*) FROM processed_emails WHERE is_spam = 1")
        spam = cur.fetchone()[0]

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
        return {
            "spam_rate_percent":  0.0,
            "suspicious_senders": [],
            "safe_percent":       100.0,
        }
