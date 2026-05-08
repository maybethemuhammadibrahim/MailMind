# backend/pipeline/summarizer.py
# ---------------------------------------------------------------
# Summarises emails using Gemini Flash. Returns a one-line
# summary, up to five key facts, and any explicit action items
# or deadlines found in the email body.
# ---------------------------------------------------------------

from pipeline.gemini import call_fast

# ---------------------------------------------------------------------------
# System prompt — sets strict output rules and JSON schema
# ---------------------------------------------------------------------------

SYSTEM = (
    "You are a professional email summarizer. Be factual, never add opinions. "
    "Return ONLY valid JSON with: "
    "one_line_summary (string, max 20 words, present tense), "
    "key_facts (array of up to 5 short strings, each max 15 words), "
    "action_items (array of strings — only explicit requests or deadlines, empty if none)."
)

# Returned whenever Gemini is unreachable or returns unparseable output
_SAFE_DEFAULT = {
    "one_line_summary": "Could not summarize this email.",
    "key_facts": [],
    "action_items": [],
}


def summarize_email(subject: str, body: str) -> dict:
    """
    Summarises an email using Gemini Flash.

    Sends the subject and the first 2 000 characters of the body to
    Gemini and returns a structured summary with a single headline,
    up to five key facts, and any actionable requests or deadlines
    explicitly mentioned in the email.

    Args:
        subject (str): the email subject line
        body    (str): the plain-text email body

    Returns:
        dict: keys are one_line_summary (str), key_facts (list[str]),
              action_items (list[str]).
              Falls back to _SAFE_DEFAULT if the Gemini call fails.
    """
    print(f"[Summarizer] Summarizing — subject: '{subject[:60]}'")
    try:
        prompt = f"Subject: {subject}\n\nEmail body:\n{body[:2000]}"
        result = call_fast(prompt, SYSTEM)
        print(
            f"[Summarizer] Done — summary: '{result.get('one_line_summary', '')[:60]}'"
        )
        return result
    except Exception as exc:
        print(f"[Summarizer] Gemini call failed: {exc} — returning safe default")
        return _SAFE_DEFAULT.copy()
