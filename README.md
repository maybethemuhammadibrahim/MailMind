# MailMind

MailMind is a FastAPI and Jinja2 email intelligence platform. It connects to Gmail via OAuth2 and uses Google Gemini alongside a local scikit-learn model to automatically classify, summarize, extract actionable items, and draft replies for incoming emails. All data is stored locally in SQLite.

## Features

* **OAuth2 Gmail Integration:** Secure authentication to read and manage emails.
* **Unread Email Fetching:** Retrieves unread emails from the last 24 hours.
* **Hybrid AI Classification:** Uses a local TF-IDF + Logistic Regression model for rapid triage (~1ms) and Google Gemini (gemini-2.5-flash-lite) for fine-grained categorization (urgent, action-required, meeting-request, order-update, newsletter, spam, fyi).
* **Automated Summarization:** Generates a one-line headline, key facts, and action items for each email.
* **Actionable Item Extraction:** Parses and stores to-dos, meeting details, and order tracking data into structured SQLite tables.
* **Context-Aware Reply Drafting:** Uses gemini-2.5-flash to draft responses based on email context and prior summaries.
* **Draft Synchronization:** Saves AI-generated drafts directly back to Gmail without sending.
* **Quality Review:** Automatically reviews drafted replies for high-priority or urgent emails.
* **Local Caching:** Stores processed emails and extraction results in SQLite to prevent duplicate API calls and ensure <100ms load times on subsequent views.
* **Analytics Dashboard:** Provides live tracking of category breakdowns, spam counts, sender analytics, and hourly email volume.
* **Rate Limit Management:** Enforces a 4.5-second global throttle and automated backoff retries to operate strictly within Gemini's 15 RPM free-tier limits.

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
