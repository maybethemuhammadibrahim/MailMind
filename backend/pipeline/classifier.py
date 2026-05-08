# backend/pipeline/classifier.py
# ---------------------------------------------------------------
# Classifies incoming emails using Gemini Flash with few-shot
# prompting. Assigns category, priority score, and flags for
# reply-needed, spam, and order emails.
# ---------------------------------------------------------------

from pipeline.gemini import call_fast

# ---------------------------------------------------------------------------
# System prompt — instructs Gemini on the exact JSON schema to return
# ---------------------------------------------------------------------------

SYSTEM = (
    "You are an email classification system. Analyze the email carefully and return "
    "ONLY valid JSON with exactly these keys: category (one of: urgent, action-required, "
    "meeting-request, order-update, newsletter, spam, fyi), priority_score (integer 1-10), "
    "requires_reply (boolean), is_spam (boolean), is_order_email (boolean), "
    "action_items (array of strings, empty if none)."
)

# ---------------------------------------------------------------------------
# Few-shot examples — shown to the model before every classification call
# so it understands category vocabulary and the expected output format.
# ---------------------------------------------------------------------------

FEW_SHOT = """Here are labelled examples to guide your classification:

Example 1:
Subject: URGENT: Production database down
From: alerts@ops.company.com
Body: All production services are failing. Database is not responding. Revenue impact ongoing.
Result: {"category":"urgent","priority_score":10,"requires_reply":true,"is_spam":false,"is_order_email":false,"action_items":["Check database server status","Page on-call engineer immediately"]}

Example 2:
Subject: Your weekly AI digest
From: digest@ainews.io
Body: This week in AI: GPT-5 rumours...
Result: {"category":"newsletter","priority_score":2,"requires_reply":false,"is_spam":false,"is_order_email":false,"action_items":[]}

Example 3:
Subject: Your Amazon order #113-456 has shipped
From: shipment-tracking@amazon.com
Body: Your order has shipped. Tracking: 1Z9999W99999999999. Estimated delivery: Thursday.
Result: {"category":"order-update","priority_score":3,"requires_reply":false,"is_spam":false,"is_order_email":true,"action_items":["Track package 1Z9999W99999999999"]}

Example 4:
Subject: Congratulations! You've won $1,000,000
From: winner@prize-claim-2024.ru
Body: Click this link to claim your prize immediately.
Result: {"category":"spam","priority_score":1,"requires_reply":false,"is_spam":true,"is_order_email":false,"action_items":[]}
"""

# Returned whenever Gemini is unreachable or returns unparseable output
_SAFE_DEFAULT = {
    "category": "fyi",
    "priority_score": 5,
    "requires_reply": False,
    "is_spam": False,
    "is_order_email": False,
    "action_items": [],
}


def _build_prompt(subject: str, sender: str, body: str) -> str:
    """
    Combines the few-shot examples with the target email fields
    into a single prompt string ready to send to Gemini.

    Args:
        subject (str): the email subject line
        sender  (str): the sender's email address
        body    (str): the plain-text email body

    Returns:
        str: fully assembled prompt (body capped at 2 000 chars)
    """
    return (
        f"{FEW_SHOT}\n"
        f"Now classify this email:\n"
        f"Subject: {subject}\n"
        f"From: {sender}\n"
        f"Body: {body[:2000]}"
    )


def classify_email(subject: str, sender: str, body: str) -> dict:
    """
    Classifies an email using Gemini Flash with few-shot prompting.

    Args:
        subject (str): email subject line
        sender  (str): sender's email address
        body    (str): plain-text email body

    Returns:
        dict: category, priority_score, requires_reply, is_spam,
              is_order_email, action_items. Safe default on failure.
    """
    print(f"[Classifier] Classifying — subject: '{subject[:60]}'")
    try:
        prompt = _build_prompt(subject, sender, body)
        result = call_fast(prompt, SYSTEM)
        print(
            f"[Classifier] Done — category={result.get('category')}, priority={result.get('priority_score')}"
        )
        return result
    except Exception as exc:
        print(f"[Classifier] Gemini call failed: {exc} — returning safe default")
        return _SAFE_DEFAULT.copy()
