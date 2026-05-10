#it loads api from .env

import os

from dotenv import load_dotenv


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))



GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/api/auth/callback")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Available models (tested and working):
#   gemini-2.5-flash       — best quality, generous free-tier quota
#   gemini-2.5-flash-lite  — fastest, lightweight, own quota bucket
#   gemini-3.1-flash-lite  — newest preview, separate quota bucket
# Deprecated (limit: 0 quota): gemini-2.0-flash, gemini-2.0-flash-lite
AI_MODEL_FAST = "gemini-2.5-flash-lite"

# Use the higher-quality model for drafting (needs more creativity)
AI_MODEL_DRAFT = "gemini-2.5-flash"

# --- App Secrets ---
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# --- Database ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "./mailmind.db")
