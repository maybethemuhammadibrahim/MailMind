# MailMind — Project Context

## Last updated
Phase 2 — Gmail OAuth and Email Fetching (2026-05-07)

## What has been built
- Project directory structure configured for a FastAPI + Jinja2 monolith
- Backend: FastAPI app with CORS, UI pages router (`routes/pages.py`), and 7 API route modules prefixed with `/api`
- Backend: 6 pipeline modules (all with placeholder functions and full docstrings)
- Backend: SQLite database module with 5 tables (processed_emails, todos, meetings, orders, settings) and deduplication helpers
- Backend: `config.py` loading env vars from `.env` via python-dotenv (REDIRECT_URI default fixed to `/api/auth/callback`)
- Backend: `requirements.txt` with pinned Python dependencies (including `jinja2`)
- Frontend/UI: Jinja2 templates (`base.html`, `home.html`, `email.html`, `crafter.html`, `orders.html`, `settings.html`) replacing React components
- Frontend/UI: Tailwind v4 integration via standalone CLI. `@theme` definitions in `static/input.css`
- Frontend/UI: Vanilla JS inside `static/app.js` for interactivity and active link management
- Root: `README.md` with complete setup instructions
- Root: `.env.example` with all required env vars
- Root: `n8n/workflow.json` placeholder

### Phase 2 additions
- **`backend/routes/auth.py`** — Full Gmail OAuth2 flow:
  - `GET /api/auth/login` — builds Google OAuth2 URL with scopes `gmail.readonly` + `gmail.modify`, redirects to Google's consent screen
  - `GET /api/auth/callback` — exchanges auth code for access + refresh tokens, saves both to `mailmind/token.json`
  - `GET /api/auth/status` — checks if `token.json` exists; used by the settings page JS to show connected/disconnected state
  - `GET /api/auth/logout` — deletes `token.json` to disconnect Gmail
  - All endpoints have inline comments explaining OAuth2 concepts (scopes, access vs. refresh tokens, why `prompt=consent` is needed)
- **`backend/routes/emails.py`** — Full Gmail API email fetching:
  - `GET /api/emails/unread` — fetches unread emails from last 24h via `google-api-python-client`; skips already-processed emails via SQLite `is_processed()` check
  - Returns list of dicts: `{ id, subject, sender, sender_email, body_plain, thread_id, timestamp }`
  - Auto-refreshes expired access tokens using stored refresh token
  - `_decode_body()` — recursive base64url decoder handling simple, multipart, and nested-multipart Gmail payloads
  - `_parse_sender()` — splits From header into display name + email address
  - `_list_messages()` — wraps Gmail messages.list with 1-retry on failure (2s delay)
  - `GET /api/emails/check/{email_id}` — returns `{"processed": bool}` for a given Gmail message ID
  - `POST /api/emails/mark-processed` — records an email as processed in SQLite
- **`backend/templates/settings.html`** — Gmail connection card added:
  - Shows "Connected" (green badge) or "Not connected" with dynamic JS status check on page load
  - "Connect Gmail" button links to `/api/auth/login`
  - "Disconnect" button calls `/api/auth/logout` and refreshes card state
  - Success banner shown after OAuth redirect (`?auth=success`)

## What is working
- Backend: All pages are routable via FastAPI Jinja2 template responses
- Frontend: Sidebar navigation shows correct active state per route via Vanilla JS
- Frontend: All pages render their mockup-matched layout shells with placeholder content via template inheritance
- Backend: All route modules are importable and registered in `main.py`
- Backend: All pipeline modules have placeholder functions returning safe defaults
- Backend: SQLite module can create all 5 tables
- **Phase 2**: Gmail OAuth login → consent screen → callback → token saved to `token.json`
- **Phase 2**: Gmail API email fetch (unread, last 24h) with token auto-refresh
- **Phase 2**: Settings page shows real-time Gmail connection status

## Known issues / incomplete
- Tailwind CSS needs to be compiled using the npx command
- No OpenAI API calls implemented (Phase 3)
- No live data connections between UI and emails list yet (Phase 7)
- All page content except settings Gmail card is placeholder — will be populated in Phases 7-11
- n8n workflow is empty placeholder (Phase 12)
- `token.json` is saved to project root — add it to `.gitignore` (contains OAuth secrets)

## Environment
- Python version: 3.11+
- n8n version: latest (install via `npm install -g n8n`)
- Tailwind CSS version: 4.x via CLI (`npx @tailwindcss/cli`)
- Key env vars required: OPENAI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI, SECRET_KEY, DATABASE_PATH
- `REDIRECT_URI` must be set to `http://localhost:8000/api/auth/callback` (in .env AND in Google Cloud Console)

## File map
```
mailmind/
├── CONTEXT.md                           — this file (project context, read every phase)
├── README.md                            — complete setup instructions for CS students
├── .env.example                         — environment variable template with comments
├── token.json                           — OAuth tokens (auto-created after /api/auth/login — DO NOT COMMIT)
├── backend/
│   ├── main.py                          — FastAPI entry point, Jinja config, routers
│   ├── config.py                        — loads env vars from .env via python-dotenv
│   ├── requirements.txt                 — pinned Python dependencies
│   ├── db/
│   │   └── sqlite.py                    — SQLite init, 5 tables, is_processed(), mark_processed()
│   ├── routes/
│   │   ├── pages.py                     — Jinja2 template UI routes
│   │   ├── auth.py                      — Gmail OAuth2: /login, /callback, /status, /logout ✅ Phase 2
│   │   ├── emails.py                    — Gmail fetch: /unread, /check, /mark-processed ✅ Phase 2
│   │   ├── pipeline.py                  — classify/summarize/draft endpoints placeholder (Phase 3)
│   │   ├── todos.py                     — todo CRUD placeholder (Phase 4)
│   │   ├── meetings.py                  — meetings listing placeholder (Phase 4)
│   │   ├── orders.py                    — order tracking placeholder (Phase 5)
│   │   └── analytics.py                 — analytics stats placeholder (Phase 6)
│   ├── templates/
│   │   ├── base.html                    — layout shell
│   │   ├── home.html                    — dashboard UI
│   │   ├── email.html                   — inbox UI
│   │   ├── crafter.html                 — compose UI
│   │   ├── orders.html                  — purchases UI
│   │   └── settings.html                — settings UI (Gmail card ✅ Phase 2)
│   ├── static/
│   │   ├── input.css                    — Tailwind theme variables
│   │   ├── style.css                    — Compiled Tailwind output
│   │   └── app.js                       — Vanilla JavaScript
│   └── pipeline/
│       ├── classifier.py                — email classification placeholder (Phase 3)
│       ├── summarizer.py                — email summarization placeholder (Phase 3)
│       ├── drafter.py                   — reply drafting placeholder (Phase 3)
│       ├── todo_extractor.py            — todo extraction placeholder (Phase 4)
│       ├── meeting_extractor.py         — meeting extraction placeholder (Phase 4)
│       └── order_extractor.py           — order extraction placeholder (Phase 5)
├── n8n/
│   └── workflow.json                    — empty n8n workflow placeholder (Phase 12)
```

## Next phase instructions

### Phase 3 — OpenAI Email Classification, Summarization, and Reply Drafting

**Read CONTEXT.md first**, then implement:

1. **`backend/pipeline/classifier.py`** — Replace placeholder with real GPT call:
   - `classify_email(subject, sender, body)` — calls GPT-4o-mini with a structured prompt
   - Returns dict: `{ category, priority_score, is_spam, confidence, reason }`
   - `category` is one of: `"urgent"`, `"meeting"`, `"order"`, `"newsletter"`, `"personal"`, `"other"`
   - `priority_score` is an integer 1–10
   - Use `response_format={"type": "json_object"}` to get structured JSON back

2. **`backend/pipeline/summarizer.py`** — Replace placeholder with real GPT call:
   - `summarize_email(subject, body)` — calls GPT-4o-mini
   - Returns a 2–3 sentence plain-text summary as a string
   - Keep the prompt tight (max 200 tokens in response)

3. **`backend/pipeline/drafter.py`** — Replace placeholder with real GPT call:
   - `draft_reply(subject, body, tone="professional")` — calls GPT-4o-mini
   - `tone` can be `"professional"`, `"casual"`, `"concise"`
   - Returns the draft reply as a plain string

4. **`backend/routes/pipeline.py`** — Wire up the pipeline endpoints:
   - `POST /api/classify` — accepts `{ email_id, subject, sender, body }`, calls `classify_email()`, saves result via `mark_processed()`, returns classification dict
   - `POST /api/summarize` — accepts `{ subject, body }`, calls `summarize_email()`, returns `{ summary }`
   - `POST /api/draft` — accepts `{ subject, body, tone }`, calls `draft_reply()`, returns `{ draft }`
   - Wrap all calls in try/except with clear error messages

5. **`backend/config.py`** — Already has `OPENAI_API_KEY`. Pass it to the OpenAI client in each pipeline module.

6. **Update CONTEXT.md** with what was built, what works, and Phase 4 instructions.

**Important notes:**
- Use `openai==1.35.3` (already in requirements.txt) — the v1 client API: `from openai import OpenAI; client = OpenAI(api_key=OPENAI_API_KEY)`
- Model: `gpt-4o-mini` for all calls (cheap, fast, good enough for email tasks)
- Every file must start with a 3-5 line comment block and every function must have a docstring
- Use `print()` for logging, no logging libraries
- Keep functions under 30 lines
- Add `token.json` to `.gitignore` if not already there
