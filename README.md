# MailMind

MailMind is a FastAPI and Jinja2 email intelligence platform. It connects to Gmail via OAuth2 and uses Google Gemini alongside a local scikit-learn model to automatically classify, summarize, extract actionable items, and draft replies for incoming emails. All data is stored locally in SQLite.

## Features
1. **Home:** Live analytics dashboard tracking category breakdowns, spam counts, sender analytics, and hourly email volume.
   
   ![Home Dashboard](screenshots/1.png)

3. **Email page:** 3-pane inbox with folder navigation displaying unread emails, AI summaries, classification tags, and extracted action items (to-dos, meetings, orders).
   
   ![Email Page Inbox](screenshots/2.png)

4. **Crafter page:** AI draft panel for context-aware reply generation, automated quality review for high-priority emails, and synchronization to Gmail drafts.
   
   ![Crafter Page AI Drafts](screenshots/3.png)

5. **Settings page:** Options to set AI reply tone, connect Gmail via OAuth2, manage API keys, and handle system configurations.
   
   ![Settings Page](screenshots/5.png)

## First-Time Local Setup

### 1. Install Prerequisites

1. Install Python 3.14+ (or 3.11+ as specified in setup notes)
2. Install Node.js 18+
3. (Optional) Install n8n globally for automations:

```bash
npm install -g n8n

```

### 2. Gmail API Setup (Google Cloud)

1. Navigate to [Google Cloud Console]().
2. Create a new project (e.g., `MailMind`).
3. Go to **APIs and Services** > **Library**, search for **Gmail API**, and enable it.
4. Go to **APIs and Services** > **OAuth consent screen**.
5. Select **External** and create the screen.
6. Fill in app details (`MailMind`) and developer contact emails.
7. Save through defaults. In **Test users**, add your Gmail address.
8. Go to **APIs and Services** > **Credentials**.
9. Click **Create Credentials** > **OAuth client ID**.
10. Choose **Web application**.
11. Add the following Authorized redirect URI:

```text
http://localhost:8000/api/auth/callback

```

12. Create credentials. Save the **Client ID** and **Client Secret**.

### 3. Gemini API Setup (Google AI Studio)

1. Navigate to [Google AI Studio]().
2. Sign in and create an API key.
3. Save the key for the environment file.

### 4. Create Environment File

Create a `.env` file in the project root. Populate it with your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
REDIRECT_URI=http://localhost:8000/api/auth/callback
SECRET_KEY=any_random_long_string_here
DATABASE_PATH=./mailmind.db

```

### 5. Install Dependencies

Initialize the Python virtual environment and install backend/frontend packages:

```bash
# From project root
python -m venv venv

# Windows PowerShell:
venv\Scripts\Activate.ps1
# Mac/Linux:
# source venv/bin/activate

pip install -r backend/requirements.txt
npm install

```

### 6. Initial Run

Run the application using two separate terminals.

**Terminal 1 (Backend Server):**

```bash
cd backend
uvicorn main:app --reload --port 8000

```

**Terminal 2 (Tailwind CSS Watcher):**

```bash
npx @tailwindcss/cli -i ./backend/static/input.css -o ./backend/static/style.css --watch

```

* App UI: [http://localhost:8000]()
* Swagger Docs: [http://localhost:8000/docs]()

### 7. Connect Gmail

1. Open [http://localhost:8000/settings]().
2. Click **Connect Gmail**.
3. Complete the Google OAuth consent flow.
4. Verify `token.json` is generated in the project root.

### 8. System Checks

Validate connectivity via these endpoints:

* Health check: `http://localhost:8000/api/health`
* Auth status: `http://localhost:8000/api/auth/status`
* Fetch unread emails: `http://localhost:8000/api/emails/unread`

---

## Usage

Follow these steps to run the application after the initial setup is complete.

1. Open a terminal in the project root.
2. Activate the virtual environment.
3. Start the backend server.

```powershell
# Windows PowerShell
venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --reload --port 8000

```

*(Optional)* Start the Tailwind watcher in a second terminal only if editing templates or styles:

```bash
npx @tailwindcss/cli -i ./backend/static/input.css -o ./backend/static/style.css --watch

```

*(Optional)* Start the automation runner if configured:

```bash
n8n start

```
