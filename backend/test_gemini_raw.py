#Sample python script to test the gemini api key directly
import os, sys
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key:
    print("ERROR: GEMINI_API_KEY not set in .env")
    sys.exit(1)

print("API Key: %s...%s" % (api_key[:8], api_key[-4:]))
print("Key length: %d chars" % len(api_key))
print()

from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
]

PROMPT = "Return JSON: {\"test\": true}"
SYSTEM = "Return only valid JSON."

for model in MODELS:
    print("Testing %s..." % model)
    try:
        response = client.models.generate_content(
            model=model,
            contents=PROMPT,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM,
                response_mime_type="application/json",
            ),
        )
        print("  OK: %s" % response.text[:100])
    except Exception as e:
        err = str(e)
        if "limit: 0" in err:
            print("  FAIL: QUOTA IS ZERO - model not available or daily limit is 0")
        elif "429" in err:
            print("  FAIL: RATE LIMITED - quota exhausted")
        elif "404" in err:
            print("  FAIL: MODEL NOT FOUND")
        else:
            print("  FAIL: %s" % err[:200])
    print()

print("If ALL models show QUOTA ZERO, your API key may be from")
print("Google Cloud Console instead of Google AI Studio.")
print("Get a free key at: https://aistudio.google.com/apikey")
