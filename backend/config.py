# backend/config.py
# ---------------------------------------------------------------
# Loads all environment variables from the .env file and exposes
# them as simple module-level constants. Every other module in
# the backend imports its secrets and paths from here.
# ---------------------------------------------------------------

import os

from dotenv import load_dotenv

# Load the .env file located one directory above backend/
# This makes all values available via os.getenv()
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- OpenAI ---
# The API key used to call GPT-4o / GPT-4o-mini for email processing
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Google OAuth ---
# These three values come from the Google Cloud Console credentials page
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# Must match exactly what you set in Google Cloud Console → Credentials → Authorized redirect URIs
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/api/auth/callback")

# --- App Secrets ---
# A random string used to sign session cookies / tokens
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# --- Database ---
# Path to the SQLite database file (relative to where uvicorn runs)
DATABASE_PATH = os.getenv("DATABASE_PATH", "./mailmind.db")
