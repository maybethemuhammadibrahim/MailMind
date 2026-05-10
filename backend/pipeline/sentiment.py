
from pipeline.gemini import call_fast


SYSTEM = (
    "You are an expert email sentiment analyst. Your job is to read an incoming email "
    "and determine the sender's emotional tone, urgency level, and whether this email "
    "requires immediate human attention (critical flag).\n\n"
    "Analyze the email carefully for:\n"
    "1. Overall emotional sentiment of the sender\n"
    "2. How intense the emotion is (0.0 = neutral, 1.0 = extremely intense)\n"
    "3. Whether this is a CRITICAL email that should bypass automation and alert the user\n"
    "4. A brief reason if the email is flagged as critical\n\n"
    "CRITICAL emails include:\n"
    "- Angry complaints or escalations\n"
    "- Legal threats or formal disputes\n"
    "- Emergency situations (system outages, safety issues)\n"
    "- Emails from VIPs or executives expressing dissatisfaction\n"
    "- Sensitive personal matters (condolences, serious health, etc.)\n\n"
    "Return ONLY valid JSON with exactly these keys:\n"
    '  "sentiment": (string — one of: positive, neutral, negative, angry, urgent, grateful, confused),\n'
    '  "intensity": (float 0.0-1.0 — how strong the emotion is),\n'
    '  "is_critical": (boolean — true if a human should handle this personally),\n'
    '  "alert_reason": (string — brief explanation if is_critical is true, empty string otherwise),\n'
    '  "recommended_tone": (string — suggested reply tone: empathetic, professional, enthusiastic, '
    "reassuring, direct, warm)\n"
    "Do NOT add any other keys."
)

_SAFE_DEFAULT = {
    "sentiment": "neutral",
    "intensity": 0.3,
    "is_critical": False,
    "alert_reason": "",
    "recommended_tone": "professional",
}


def analyze_sentiment(subject: str, body: str, sender: str) -> dict:
    print(f"[Sentiment] Analyzing — subject: '{subject[:60]}'")

    prompt = (
        f"Analyze the sentiment of this email:\n\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Body:\n{body[:2000]}"
    )

    try:
        result = call_fast(prompt, SYSTEM)
        print(
            f"[Sentiment] Done — sentiment={result.get('sentiment')}, "
            f"intensity={result.get('intensity')}, "
            f"is_critical={result.get('is_critical')}"
        )
        return result
    except Exception as exc:
        print(f"[Sentiment] Gemini call failed: {exc} — returning neutral default")
        return _SAFE_DEFAULT.copy()
