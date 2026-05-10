
import json
import threading
import time

from config import AI_MODEL_DRAFT, AI_MODEL_FAST, GEMINI_API_KEY
from google import genai
from google.genai import types

_throttle_lock = threading.Lock()
_last_call_time = 0.0
MIN_CALL_DELAY = 4.5


def _throttle():
    global _last_call_time
    with _throttle_lock:
        now = time.time()
        wait = max(0, MIN_CALL_DELAY - (now - _last_call_time))
        if wait > 0:
            time.sleep(wait)
        _last_call_time = time.time()


def get_client():
    return genai.Client(api_key=GEMINI_API_KEY)


def call_gemini(prompt: str, system: str, model: str = None, temperature: float = None) -> dict:
    model = model or AI_MODEL_FAST
    client = get_client()

    _throttle()

    config_kwargs = {
        "system_instruction": system,
        "response_mime_type": "application/json",
    }
    if temperature is not None:
        config_kwargs["temperature"] = temperature

    config = types.GenerateContentConfig(**config_kwargs)

    delays = [2, 12, 20]

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)

        except Exception as exc:
            error_str = str(exc)
            is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str

            if attempt < 2:
                wait = delays[attempt]
                if is_rate_limit:
                    wait = max(wait, 12)
                print(f"[Gemini] Attempt {attempt+1} failed ({error_str[:80]}). Retrying in {wait}s…")
                time.sleep(wait)
            else:
                print(f"[Gemini] All 3 attempts failed: {error_str[:120]}")
                raise


def call_fast(prompt: str, system: str) -> dict:
    return call_gemini(prompt, system, model=AI_MODEL_FAST)


def call_draft(prompt: str, system: str) -> dict:
    return call_gemini(prompt, system, model=AI_MODEL_DRAFT, temperature=0.9)


def call_review(prompt: str, system: str) -> dict:
    return call_gemini(prompt, system, model=AI_MODEL_FAST, temperature=0.2)
