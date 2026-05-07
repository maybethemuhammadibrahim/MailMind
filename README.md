# MailMind — AI-Powered Email Assistant

MailMind is a semester project that uses AI (OpenAI GPT-4o) to automatically classify,
summarise, and draft replies to your Gmail inbox. It also extracts to-do items, meeting
events, and order/purchase data from emails, presenting everything in a clean dashboard.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| n8n | latest | `npm install -g n8n` |

---

## 1. Google Cloud Setup (Gmail API)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a **new project** (e.g. "MailMind")
3. Enable the **Gmail API**: APIs & Services → Library → search "Gmail API" → Enable
4. Create **OAuth 2.0 credentials**:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Web application**
   - Authorised redirect URIs: `http://localhost:8000/auth/callback`
   - Download the JSON file — you'll need `client_id` and `client_secret`
5. Configure the **OAuth consent screen**:
   - User type: External (or Internal if using a Workspace account)
   - Add scopes: `gmail.readonly`, `gmail.modify`
   - Add your email as a test user

---

## 2. OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Go to API Keys → Create new secret key
4. Copy the key — you'll paste it into `.env`

---

## 3. Environment Setup

```bash
# Clone or navigate to the project folder
cd mailmind

# ----- Backend -----
# Create a Python virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r backend/requirements.txt
```

---

## 4. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Open .env in your editor and fill in:
#   OPENAI_API_KEY       — from step 2
#   GOOGLE_CLIENT_ID     — from step 1
#   GOOGLE_CLIENT_SECRET — from step 1
#   SECRET_KEY           — any random string (run: python -c "import secrets; print(secrets.token_hex(32))")
```

---

## 5. Running the App

### Backend (FastAPI + Jinja2)

```bash
cd backend
uvicorn main:app --reload
# Server starts at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Tailwind CSS Compilation

Since the app uses a Jinja2 monolith, you need to run the Tailwind standalone CLI to compile changes to `input.css` into `style.css`:

```bash
# From the root directory:
npx @tailwindcss/cli -i ./backend/static/input.css -o ./backend/static/style.css --watch
```

### n8n (Workflow Automation)

```bash
n8n start
# Opens at http://localhost:5678
# Go to Workflows → Import → select n8n/workflow.json
```

---

## Project Structure

```
mailmind/
├── CONTEXT.md                  ← project context (read/update every phase)
├── README.md                   ← this file
├── .env.example                ← env var template
├── backend/
│   ├── main.py                 ← FastAPI entry point + UI routing
│   ├── config.py               ← env var loading
│   ├── requirements.txt        ← Python dependencies
│   ├── db/
│   │   └── sqlite.py           ← database init + helpers
│   ├── routes/
│   │   ├── auth.py             ← Gmail OAuth
│   │   ├── pages.py            ← Jinja2 UI rendering routes
│   │   ├── emails.py           ← fetch + classify + deduplicate
│   │   ├── pipeline.py         ← classify / summarize / draft endpoints
│   │   ├── todos.py            ← to-do item endpoints
│   │   ├── meetings.py         ← meeting event endpoints
│   │   ├── orders.py           ← order/purchase tracking
│   │   └── analytics.py        ← spam/source/security stats
│   ├── pipeline/
│   │   ├── classifier.py       ← email classification (GPT-4o-mini)
│   │   ├── summarizer.py       ← email summarisation (GPT-4o-mini)
│   │   ├── drafter.py          ← reply drafting (GPT-4o)
│   │   ├── todo_extractor.py   ← to-do extraction (GPT-4o-mini)
│   │   ├── meeting_extractor.py← meeting extraction (GPT-4o-mini)
│   │   └── order_extractor.py  ← order extraction (GPT-4o-mini)
│   ├── templates/              ← Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── email.html
│   │   ├── crafter.html
│   │   ├── orders.html
│   │   └── settings.html
│   └── static/                 ← Static assets
│       ├── input.css           ← Tailwind @theme tokens
│       ├── style.css           ← Compiled CSS
│       └── app.js              ← Vanilla JS logic
├── n8n/
│   └── workflow.json           ← n8n automation workflow
```

---

## Phase Checklist

```
Phase 1  - [x] Project runs, Jinja2 template monolith setup with Tailwind CLI
Phase 2  - [ ] Gmail OAuth login works, unread emails fetched
Phase 3  - [ ] Classify / summarize / draft pipeline returns correct JSON
Phase 4  - [ ] Todos and meetings extracted and stored in SQLite
Phase 5  - [ ] Order emails detected and structured data stored
Phase 6  - [ ] Analytics endpoint returns correct stats
Phase 7  - [ ] Home page renders todos, meetings, charts from live data
Phase 8  - [ ] Email page shows inbox, clicking email shows AI draft
Phase 9  - [ ] Crafter generates full email from tone + prompt
Phase 10 - [ ] Orders page shows all orders with correct status badges
Phase 11 - [ ] Settings saved to DB, Gmail connected/disconnected works
Phase 12 - [ ] n8n workflow runs end-to-end, Gmail Draft appears in inbox
```

# Phase 1 Walkthrough — Setup, Skeleton, and README

## Summary

Phase 1 of MailMind is complete. The application has been migrated from a decoupled React architecture to a Jinja2 monolith powered by FastAPI, avoiding build steps and minimizing the tech stack while keeping the same UI. Tailwind CSS v4 is used via the standalone CLI. All base templates are successfully rendered.
