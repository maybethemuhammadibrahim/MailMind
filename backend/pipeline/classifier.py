# backend/pipeline/classifier.py
# ---------------------------------------------------------------
# Hybrid email classifier: sklearn handles coarse triage (spam,
# promotions, forum, social_media, updates, verify_code), then
# Gemini Flash refines with full sentiment analysis and may
# upgrade to fine-grained categories (urgent, action-required,
# meeting-request, order-update).
#
# The sklearn prediction is injected into the Gemini prompt as
# a starting hint. Gemini returns the complete JSON dict with
# all keys the rest of the app depends on.
# ---------------------------------------------------------------

from pipeline.gemini import call_fast
from pipeline.sklearn_classifier import predict_category

# ---------------------------------------------------------------------------
# System prompt — instructs Gemini on the exact JSON schema to return.
# Includes sentiment analysis keys so we get classification AND
# sentiment in one call instead of two separate API requests.
# ---------------------------------------------------------------------------

SYSTEM = (
    "You are an email classification and sentiment analysis system. "
    "Analyze the email carefully and return ONLY valid JSON with exactly these keys: "
    "category (one of: urgent, action-required, meeting-request, order-update, "
    "spam, promotions, forum, social_media, updates, verify_code), "
    "priority_score (integer 1-10), "
    "requires_reply (boolean), "
    "is_spam (boolean), "
    "is_order_email (boolean), "
    "action_items (array of strings, empty if none), "
    "sender_sentiment (one of: positive, neutral, negative, angry, urgent, grateful, confused), "
    "sentiment_intensity (float 0.0-1.0 — how strong the emotion is), "
    "is_critical (boolean — true only for angry complaints, legal threats, emergencies, "
    "VIP escalations, or sensitive personal matters that need human attention), "
    "alert_reason (string — brief explanation if is_critical is true, empty string otherwise), "
    "recommended_reply_tone (one of: empathetic, professional, enthusiastic, reassuring, direct, warm)."
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
Result: {"category":"urgent","priority_score":10,"requires_reply":true,"is_spam":false,"is_order_email":false,"action_items":["Check database server status","Page on-call engineer immediately"],"sender_sentiment":"urgent","sentiment_intensity":0.9,"is_critical":true,"alert_reason":"Production outage with revenue impact","recommended_reply_tone":"empathetic"}

Example 2:
Subject: Your weekly AI digest
From: digest@ainews.io
Body: This week in AI: GPT-5 rumours...
Result: {"category":"promotions","priority_score":2,"requires_reply":false,"is_spam":false,"is_order_email":false,"action_items":[],"sender_sentiment":"neutral","sentiment_intensity":0.1,"is_critical":false,"alert_reason":"","recommended_reply_tone":"professional"}

Example 3:
Subject: Your Amazon order #113-456 has shipped
From: shipment-tracking@amazon.com
Body: Your order has shipped. Tracking: 1Z9999W99999999999. Estimated delivery: Thursday.
Result: {"category":"order-update","priority_score":3,"requires_reply":false,"is_spam":false,"is_order_email":true,"action_items":["Track package 1Z9999W99999999999"],"sender_sentiment":"neutral","sentiment_intensity":0.2,"is_critical":false,"alert_reason":"","recommended_reply_tone":"professional"}

Example 4:
Subject: Congratulations! You've won $1,000,000
From: winner@prize-claim-2024.ru
Body: Click this link to claim your prize immediately.
Result: {"category":"spam","priority_score":1,"requires_reply":false,"is_spam":true,"is_order_email":false,"action_items":[],"sender_sentiment":"neutral","sentiment_intensity":0.1,"is_critical":false,"alert_reason":"","recommended_reply_tone":"direct"}

Example 5:
Subject: John mentioned you in a comment
From: notifications@linkedin.com
Body: John Smith commented on your post: "Great insights on the market trends!"
Result: {"category":"social_media","priority_score":2,"requires_reply":false,"is_spam":false,"is_order_email":false,"action_items":[],"sender_sentiment":"positive","sentiment_intensity":0.3,"is_critical":false,"alert_reason":"","recommended_reply_tone":"warm"}

Example 6:
Subject: New reply in thread: Best CI/CD practices
From: noreply@devforum.io
Body: User42 replied to your thread in the DevOps section: "We switched to GitHub Actions and..."
Result: {"category":"forum","priority_score":3,"requires_reply":false,"is_spam":false,"is_order_email":false,"action_items":[],"sender_sentiment":"neutral","sentiment_intensity":0.2,"is_critical":false,"alert_reason":"","recommended_reply_tone":"professional"}
"""

# Returned whenever Gemini is unreachable or returns unparseable output.
# Using "unknown" instead of a real label so failed classifications are
# flagged for manual review rather than silently categorised.
_SAFE_DEFAULT = {
    "category": "unknown",
    "priority_score": 5,
    "requires_reply": False,
    "is_spam": False,
    "is_order_email": False,
    "action_items": [],
    "sender_sentiment": "neutral",
    "sentiment_intensity": 0.3,
    "is_critical": False,
    "alert_reason": "",
    "recommended_reply_tone": "professional",
}


def _build_prompt(subject: str, sender: str, body: str, sklearn_category: str) -> str:
    """
    Combines the few-shot examples with the target email fields and the
    sklearn pre-classification hint into a single prompt for Gemini.

    Args:
        subject          (str): the email subject line
        sender           (str): the sender's email address
        body             (str): the plain-text email body
        sklearn_category (str): coarse category from the local ML model

    Returns:
        str: fully assembled prompt (body capped at 2 000 chars)
    """
    sklearn_hint = (
        f"\nA local ML model has pre-classified this email as: {sklearn_category}. "
        f"Use this as your starting point for the category field. "
        f"You MAY override it to: urgent, action-required, meeting-request, or order-update "
        f"if the email content clearly warrants it. Otherwise default to the ML prediction.\n"
        f"The ML model predicts one of: spam, promotions, forum, social_media, updates, verify_code.\n"
    )

    return (
        f"{FEW_SHOT}\n"
        f"{sklearn_hint}\n"
        f"Now classify this email:\n"
        f"Subject: {subject}\n"
        f"From: {sender}\n"
        f"Body: {body[:2000]}"
    )


def _validate_result(result: dict) -> dict:
    """
    Merges Gemini's response with _SAFE_DEFAULT to fill any missing keys
    and clamps values to valid ranges. Ensures downstream code never
    encounters missing or out-of-range fields.

    Args:
        result (dict): raw dict returned by Gemini

    Returns:
        dict: validated result with all required keys present
    """
    validated = _SAFE_DEFAULT.copy()
    validated.update({k: v for k, v in result.items() if v is not None})

    # Clamp priority score to 1-10 range
    try:
        validated["priority_score"] = max(1, min(10, int(validated["priority_score"])))
    except (ValueError, TypeError):
        validated["priority_score"] = 5

    # Clamp sentiment intensity to 0.0-1.0
    try:
        validated["sentiment_intensity"] = max(0.0, min(1.0, float(validated["sentiment_intensity"])))
    except (ValueError, TypeError):
        validated["sentiment_intensity"] = 0.3

    return validated


def classify_email(subject: str, sender: str, body: str) -> dict:
    """
    Hybrid classifier: runs local sklearn model for coarse triage,
    then passes the prediction as context to Gemini for fine-grained
    classification and full sentiment analysis.

    The sklearn model predicts one of: spam, promotions, forum,
    social_media, updates, verify_code.
    Gemini may upgrade to: urgent, action-required, meeting-request,
    or order-update if the content warrants it.

    Args:
        subject (str): email subject line
        sender  (str): sender's email address
        body    (str): plain-text email body

    Returns:
        dict: category, priority_score, requires_reply, is_spam,
              is_order_email, action_items, sender_sentiment,
              sentiment_intensity, is_critical, alert_reason,
              recommended_reply_tone. Safe default on failure.
    """
    # --- Step 1: Local sklearn coarse triage ---
    try:
        sklearn_category: str = predict_category(subject, body)
        print(f"[Classifier] sklearn pre-classification: {sklearn_category}")
    except RuntimeError as exc:
        # Model file not found — fall back to no hint
        print(f"[Classifier] sklearn unavailable: {exc}")
        sklearn_category = "updates"  # neutral fallback

    # --- Step 2: Gemini fine-grained classification + sentiment ---
    print(f"[Classifier] Classifying — subject: '{subject[:60]}'")
    try:
        prompt = _build_prompt(subject, sender, body, sklearn_category)
        result = call_fast(prompt, SYSTEM)
        validated = _validate_result(result)
        print(
            f"[Classifier] Done — category={validated.get('category')}, "
            f"priority={validated.get('priority_score')}, "
            f"sentiment={validated.get('sender_sentiment')}"
        )
        return validated
    except Exception as exc:
        print(f"[Classifier] Gemini call failed: {exc} — returning safe default")
        # If Gemini fails, still use the sklearn category as a better-than-nothing answer
        fallback = _SAFE_DEFAULT.copy()
        fallback["category"] = sklearn_category
        fallback["is_spam"] = sklearn_category == "spam"
        return fallback
