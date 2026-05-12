# MailBunny

MailMind is a FastAPI + Jinja2 email assistant that connects to Gmail, uses Google Gemini for AI tasks, and stores project data in SQLite.

## First-Time Local Setup

### 1. Install prerequisites

1. Install Python 3.11+
2. Install Node.js 18+
3. (Optional) Install n8n globally if you will run automations

```bash
npm install -g n8n
```

### 2. Gmail API setup (Google Cloud)

1. Go to https://console.cloud.google.com
2. Create a new Google Cloud project (example: MailMind)
3. Open APIs and Services -> Library
4. Search for Gmail API and click Enable
5. Open APIs and Services -> OAuth consent screen
6. Choose External and create the consent screen
7. Fill app details:
   - App name: MailMind
   - User support email: your email
   - Developer contact email: your email
8. Save and continue through defaults
9. In Test users, add your Gmail address
10. Open APIs and Services -> Credentials
11. Click Create Credentials -> OAuth client ID
12. Choose Web application
13. Add this Authorized redirect URI exactly:

```text
http://localhost:8000/api/auth/callback
```

14. Create credentials and copy:
   - Client ID
   - Client Secret

### 3. Gemini API setup (Google AI Studio)

1. Go to https://aistudio.google.com or https://ai.google.dev
2. Sign in with your Google account
3. Create an API key
4. Copy the key value (this will be used as GEMINI_API_KEY)

### 4. Create environment file

Create a file named `.env` in the project root with this content and fill your real values:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
REDIRECT_URI=http://localhost:8000/api/auth/callback
SECRET_KEY=any_random_long_string_here
DATABASE_PATH=./mailmind.db
```

### 5. Install dependencies

From project root:

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Then install backend and frontend dependencies:

```bash
pip install -r backend/requirements.txt
npm install
```

### 6. Run project for the first time

Use two terminals.

Terminal 1 (backend server):

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Terminal 2 (Tailwind CSS watch/build):

```bash
npx @tailwindcss/cli -i ./backend/static/input.css -o ./backend/static/style.css --watch
```

Open app and docs:

- App UI: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### 7. Connect Gmail from the app

1. Open http://localhost:8000/settings
2. Click Connect Gmail
3. Complete Google consent flow
4. After success, token.json is created in project root

### 8. Quick connectivity checks

1. Health check: http://localhost:8000/api/health
2. Auth status: http://localhost:8000/api/auth/status
3. Fetch recent unread emails (after auth): http://localhost:8000/api/emails/unread

## How To Run After Installation Is Done

Whenever you reopen the project:

1. Open terminal in project root
2. Activate virtual environment
3. Start backend
4. Start Tailwind watcher only if you are editing styles/templates

Commands:

```powershell
# From project root
venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --reload --port 8000
```

In a second terminal (from project root), only when needed:

```bash
npx @tailwindcss/cli -i ./backend/static/input.css -o ./backend/static/style.css --watch
```

Optional automation runner:

```bash
n8n start
```

That is enough to run MailMind locally after initial setup.
