# backend/pipeline/gemini.py
# ---------------------------------------------------------------
# Shared Google Gemini client used by all three pipeline modules
# (classifier, summarizer, drafter). Keeps the API key, model
# names, and retry logic in one place so each pipeline function
# stays short and focused on its prompt.
# ---------------------------------------------------------------

import json
import time

from config import AI_MODEL_DRAFT, AI_MODEL_FAST, GEMINI_API_KEY
from google import genai
from google.genai import types


def get_client():
    """
    Returns an authenticated Gemini client using the key from .env.
    The client is lightweight — creating one per call is fine.

    Returns:
        genai.Client: ready-to-use Gemini client
    """
    return genai.Client(api_key=GEMINI_API_KEY)


def call_gemini(prompt: str, system: str, model: str = None) -> dict:
    """
    Makes a single JSON-mode Gemini call with one automatic retry.

    response_mime_type='application/json' tells Gemini to always
    return valid JSON — no markdown fences, no extra text.
    If the first attempt fails (network glitch, rate-limit, etc.)
    we wait 2 seconds and try once more before raising.

    Args:
        prompt (str): the user-facing message (email content, etc.)
        system (str): the system instruction that shapes the output
        model  (str): override the default model (uses AI_MODEL_FAST)

    Returns:
        dict: parsed JSON from Gemini's response

    Raises:
        Exception: re-raised after the second failed attempt
    """
    model = model or AI_MODEL_FAST
    client = get_client()

    config = types.GenerateContentConfig(
        system_instruction=system,
        # Forces the model to return well-formed JSON every time
        response_mime_type="application/json",
    )

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)

        except Exception as exc:
            if attempt == 0:
                print(f"[Gemini] Attempt 1 failed ({exc}). Retrying in 2s…")
                time.sleep(2)
            else:
                print(f"[Gemini] Both attempts failed: {exc}")
                raise


# Convenience aliases so pipeline modules can import by intent
def call_fast(prompt: str, system: str) -> dict:
    """Calls the fast model (gemini-2.0-flash) — use for classify + summarize."""
    return call_gemini(prompt, system, model=AI_MODEL_FAST)


def call_draft(prompt: str, system: str) -> dict:
    """Calls the draft model — same by default, swap for gemini-1.5-pro if needed."""
    return call_gemini(prompt, system, model=AI_MODEL_DRAFT)
