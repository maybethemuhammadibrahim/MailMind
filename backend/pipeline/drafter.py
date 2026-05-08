# backend/pipeline/drafter.py
# ---------------------------------------------------------------
# Drafts professional email replies using Gemini. Injects the
# classification and summary as context so the model produces a
# tone-matched, ready-to-send reply with a confidence score.
# ---------------------------------------------------------------

from pipeline.gemini import call_draft

# ---------------------------------------------------------------------------
# System prompt — tone rules and exact JSON schema for the draft output
# ---------------------------------------------------------------------------

SYSTEM = (
    "You are a professional email assistant drafting a reply on behalf of the recipient. "
    "Use the classification and summary to understand urgency and what is needed. "
    "Be concise, clear, and direct. Match tone to category: "
    "urgent → brief and action-oriented; "
    "meeting-request → confirm or propose alternative; "
    "action-required → acknowledge and commit to a deadline; "
    "newsletter/fyi → no reply needed (return confidence_score 0.1); "
    "spam → no reply needed (return confidence_score 0.0). "
    "Return ONLY valid JSON with: "
    "draft_reply (string, full reply text ready to send, include greeting and sign-off), "
    "confidence_score (float 0.0-1.0, how appropriate a reply is), "
    "suggested_subject (string, reply subject line like 'Re: Original Subject')."
)


def _build_prompt(subject: str, body: str, classification: dict, summary: dict) -> str:
    """
    Assembles the drafting prompt by injecting classification and
    summary context above the original email so Gemini knows the
    urgency level, required actions, and key facts before composing.

    Args:
        subject        (str):  the original email subject line
        body           (str):  the original email body
        classification (dict): output from classify_email()
        summary        (dict): output from summarize_email()

    Returns:
        str: fully assembled prompt (body capped at 2 000 chars)
    """
    action_items = ", ".join(summary.get("action_items", [])) or "none"
    key_facts = "; ".join(summary.get("key_facts", [])) or "none"
    return (
        f"Category: {classification.get('category', 'fyi')}\n"
        f"Priority score: {classification.get('priority_score', 5)}/10\n"
        f"Requires reply: {classification.get('requires_reply', False)}\n"
        f"Summary: {summary.get('one_line_summary', '')}\n"
        f"Key facts: {key_facts}\n"
        f"Action items: {action_items}\n\n"
        f"Original email — Subject: {subject}\n"
        f"Body:\n{body[:2000]}"
    )


def draft_reply(subject: str, body: str, classification: dict, summary: dict) -> dict:
    """
    Drafts a professional reply using Gemini with classification and summary context.

    Args:
        subject        (str):  original email subject
        body           (str):  original email body
        classification (dict): output from classify_email()
        summary        (dict): output from summarize_email()

    Returns:
        dict: draft_reply (str), confidence_score (float), suggested_subject (str).
              Falls back to a polite acknowledgement on failure.
    """
    category = classification.get("category", "unknown")
    print(f"[Drafter] Drafting — subject: '{subject[:60]}', category: {category}")
    try:
        result = call_draft(
            _build_prompt(subject, body, classification, summary), SYSTEM
        )
        print(f"[Drafter] Done — confidence_score: {result.get('confidence_score')}")
        return result
    except Exception as exc:
        print(f"[Drafter] Gemini call failed: {exc} — returning safe default")
        return {
            "draft_reply": f"Thank you for your email regarding '{subject}'. I will review and respond shortly.",
            "confidence_score": 0.5,
            "suggested_subject": f"Re: {subject}",
        }
