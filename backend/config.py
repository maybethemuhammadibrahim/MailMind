# backend/config.py
# ---------------------------------------------------------------
# Loads all environment variables from the .env file and exposes
# them as simple module-level constants. Every other module in
# the backend imports its secrets and paths from here.
# ---------------------------------------------------------------

import os

from dotenv import load_dotenv

# Load the .env file located one directory above backend/
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- Google OAuth (Gmail) ---
# From: console.cloud.google.com → APIs & Services → Credentials → OAuth 2.0 Client ID
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# Must match EXACTLY what is in Google Cloud Console → Authorized redirect URIs
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/api/auth/callback")

# --- AI: Google Gemini ---
# Get your free API key at: https://ai.google.dev/  (Google AI Studio)
# Free tier: 1,500 requests/day · 1M tokens/day — no credit card needed.
# We use the native google-genai SDK (no OpenAI wrapper).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# gemini-2.5-flash: confirmed working on this key.
# If you hit quota errors, try: gemini-2.0-flash-lite, gemini-flash-latest
AI_MODEL_FAST = "gemini-2.5-flash"

# Same model for drafting; upgrade to gemini-2.5-pro for higher quality
AI_MODEL_DRAFT = "gemini-2.5-flash"

# --- App Secrets ---
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# --- Database ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "./mailmind.db")
