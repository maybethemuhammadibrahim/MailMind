How to connect your Google API (step-by-step)

### Step 1 — Create a Google Cloud Project

1. Go to **[console.cloud.google.com](https://console.cloud.google.com)**
2. Click the project dropdown at the top → **"New Project"**
3. Give it a name like `MailMind` → **Create**
4. Make sure it's selected in the dropdown

### Step 2 — Enable the Gmail API

1. In the left sidebar go to **APIs & Services → Library**
2. Search for **"Gmail API"**
3. Click it → **Enable**

### Step 3 — Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → **Create**
3. Fill in:
   - **App name**: `MailMind`
   - **User support email**: your email
   - **Developer contact email**: your email
4. Click **Save and Continue** through the rest (leave defaults)
5. On the **Test users** page, add your own Gmail address → **Save**

> ⚠️ While in "Testing" mode, only the emails you add as test users can log in. That's fine for development.

### Step 4 — Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **"+ Create Credentials" → OAuth client ID**
3. Choose **Application type: Web application**
4. Give it a name: `MailMind Dev`
5. Under **Authorized redirect URIs**, click **Add URI** and enter:
   ```/dev/null/uri.txt#L1
   http://localhost:8000/api/auth/callback
   ```
6. Click **Create**
7. A popup shows your **Client ID** and **Client Secret** — copy both

### Step 5 — Fill in your `.env` file

Create `mailmind/.env` (copy from `.env.example`) and fill in:

```/dev/null/.env.example#L1-6
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
REDIRECT_URI=http://localhost:8000/api/auth/callback
SECRET_KEY=any-random-string-here
DATABASE_PATH=./mailmind.db
OPENAI_API_KEY=sk-...   # leave blank for now, needed in Phase 3
```

### Step 6 — Start the server and connect

```/dev/null/terminal.sh#L1-4
# From mailmind/backend/
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open your browser and go to:
- **`http://localhost:8000/settings`** — you'll see the Gmail card showing "Not connected"
- Click **Connect Gmail** → Google consent screen appears → click **Allow**
- You'll be redirected back to `/settings` with a green "Connected" banner

A `token.json` file is created at the project root — this is your OAuth tokens. It's in `.gitignore` so it won't be committed.

### Step 7 — Test email fetching

Visit **`http://localhost:8000/api/emails/unread`** in your browser or use the `/docs` page. You should see a JSON list of your unread emails from the last 24 hours.