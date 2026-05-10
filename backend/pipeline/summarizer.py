
from pipeline.gemini import call_fast


SYSTEM = (
    "You are a professional email summarizer. Be factual, never add opinions. "
    "Return ONLY valid JSON with: "
    "one_line_summary (string, max 20 words, present tense), "
    "key_facts (array of up to 5 short strings, each max 15 words), "
    "action_items (array of strings — only explicit requests or deadlines, empty if none)."
)

_SAFE_DEFAULT = {
    "one_line_summary": "Could not summarize this email.",
    "key_facts": [],
    "action_items": [],
}


def summarize_email(subject: str, body: str) -> dict:
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
