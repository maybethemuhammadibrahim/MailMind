# MailMind — Project Context

## Last updated
Phase 3 — AI Pipeline: Classify, Summarize, Draft (2026-05-08)

## What has been built
- Project directory structure configured for a FastAPI + Jinja2 monolith
- Backend: FastAPI app with CORS, UI pages router (`routes/pages.py`), and 8 API route modules prefixed with `/api`
- Backend: 3 AI pipeline modules using **Google Gemini** (not OpenAI) via the native `google-genai` SDK
- Backend: Shared Gemini client (`pipeline/gemini.py`) with JSON-mode, retry logic, and convenience aliases
- Backend: SQLite database module with 5 tables (processed_emails, todos, meetings, orders, settings) and deduplication helpers
- Backend: `config.py` loading env vars from `.env` via python-dotenv — uses `GEMINI_API_KEY` (no OpenAI key required)
- Backend: `requirements.txt` with pinned Python dependencies including `google-genai>=2.0.0` (OpenAI dependency removed)
- Frontend/UI: Jinja2 templates (`base.html`, `home.html`, `email.html`, `crafter.html`, `orders.html`, `settings.html`, `dev.html`)
- Frontend/UI: Tailwind v4 integration via standalone CLI. `@theme` definitions in `static/input.css`
- Frontend/UI: Vanilla JS inside templates for interactivity — pipeline calls, inbox sync, analytics rendering
- Root: `README.md` with complete setup instructions
- Root: `.env.example` with all required env vars

### Phase 2 additions
- **`backend/routes/auth.py`** — Full Gmail OAuth2 flow:
  - `GET /api/auth/login` — builds Google OAuth2 URL with scopes `gmail.readonly` + `gmail.modify`, redirects to Google's consent screen
  - `GET /api/auth/callback` — exchanges auth code for access + refresh tokens, saves both to `mailmind/token.json`
  - `GET /api/auth/status` — checks if `token.json` exists; used by the settings page JS to show connected/disconnected state
  - `GET /api/auth/logout` — deletes `token.json` to disconnect Gmail
- **`backend/routes/emails.py`** — Full Gmail API email fetching:
  - `GET /api/emails/unread` — fetches unread emails from last 24h via `google-api-python-client`
  - Auto-refreshes expired access tokens using stored refresh token
  - `GET /api/emails/check/{email_id}` — returns `{"processed": bool}` for a given Gmail message ID
  - `POST /api/emails/mark-processed` — records an email as processed in SQLite
- **`backend/templates/settings.html`** — Gmail connection card with live status check

### Phase 3 additions
- **`backend/pipeline/gemini.py`** — Shared Google Gemini client:
  - Uses the native `google-genai` SDK (not the OpenAI compatibility wrapper)
  - `call_gemini(prompt, system, model)` — JSON-mode call with `response_mime_type='application/json'`
  - Automatic 1-retry with 2-second backoff on failure
  - `call_fast()` — alias for the fast model (gemini-2.5-flash), used by classifier + summarizer
  - `call_draft()` — alias for the draft model (gemini-2.5-flash, upgradeable to gemini-2.5-pro)
- **`backend/pipeline/classifier.py`** — Email classification using Gemini:
  - `classify_email(subject, sender, body)` with 4 few-shot examples
  - Returns: `{ category, priority_score, requires_reply, is_spam, is_order_email, action_items }`
  - Categories: urgent, action-required, meeting-request, order-update, newsletter, spam, fyi
- **`backend/pipeline/summarizer.py`** — Email summarization using Gemini:
  - `summarize_email(subject, body)`
  - Returns: `{ one_line_summary, key_facts, action_items }`
- **`backend/pipeline/drafter.py`** — Reply drafting using Gemini:
  - `draft_reply(subject, body, classification, summary)` — injects classification + summary context
  - Returns: `{ draft_reply, confidence_score, suggested_subject }`
- **`backend/routes/pipeline.py`** — AI pipeline REST endpoints:
  - `POST /api/classify` — classifies a single email, saves to DB via `mark_processed()`
  - `POST /api/summarize` — summarizes an email (read-only, no DB write)
  - `POST /api/draft` — drafts a reply given pre-computed classification + summary
  - `POST /api/process-email` — runs all three stages in sequence, returns combined result
  - All endpoints use Pydantic request models for validation
- **`backend/routes/analytics.py`** — Dashboard analytics:
  - `GET /api/analytics/summary` — returns `{ total_processed, categories, spam_blocked, requires_reply_count }` from real DB queries
- **`backend/routes/dev.py`** — Developer sandbox endpoints:
  - `GET /api/dev/status` — live status of Gmail, AI API, and DB
  - `GET /api/dev/db-stats` — row counts for all 5 tables
  - `POST /api/dev/test-ai` — sends a test email to Gemini, returns classification JSON + latency
  - `GET /api/dev/emails` — fetches Gmail emails with `in_db` annotation
- **`backend/templates/dev.html`** — Full developer console UI:
  - System status cards (Gmail, Gemini AI, SQLite)
  - Email fetch table with DB coverage flags
  - AI classification test with live input fields
  - Database table stats
- **`backend/templates/email.html`** — Fully wired 3-pane inbox:
  - Left panel: inbox list with Important/All tabs, sync button, loading/empty states
  - Center panel: email content display with summary bar, category badges, sender info
  - Right panel: AI Draft Assistant with editable textarea, confidence badge, copy/regenerate/send buttons
  - JavaScript calls `/api/process-email` on email selection, caches results, supports re-drafting
- **`backend/templates/home.html`** — Dashboard with live analytics:
  - Quick-stats bar: Emails processed, Spam blocked, Needs reply
  - Category breakdown bar chart (CSS-based, no chart library)
  - Tasks and meetings remain as empty states (Phase 4)
- **`backend/config.py`** — Updated for Gemini:
  - `GEMINI_API_KEY` loaded from `.env`
  - `AI_MODEL_FAST = "gemini-2.5-flash"` — for classify + summarize
  - `AI_MODEL_DRAFT = "gemini-2.5-flash"` — for drafting (upgradeable to gemini-2.5-pro)
  - OpenAI references removed

## What is working
- Backend: All pages are routable via FastAPI Jinja2 template responses
- Frontend: Sidebar navigation shows correct active state per route
- Frontend: All pages render their mockup-matched layout shells
- Backend: All route modules are importable and registered in `main.py`
- Backend: SQLite module can create all 5 tables
- **Phase 2**: Gmail OAuth login → consent screen → callback → token saved to `token.json`
- **Phase 2**: Gmail API email fetch (unread, last 24h) with token auto-refresh
- **Phase 2**: Settings page shows real-time Gmail connection status
- **Phase 3**: Gemini-powered email classification with few-shot prompting
- **Phase 3**: Gemini-powered email summarization (one-line + key facts + action items)
- **Phase 3**: Gemini-powered reply drafting with classification/summary context
- **Phase 3**: Full pipeline endpoint (`POST /api/process-email`) runs classify → summarize → draft in sequence
- **Phase 3**: Email page loads inbox, runs AI pipeline on click, displays draft with confidence score
- **Phase 3**: Home dashboard shows live analytics from processed emails
- **Phase 3**: Developer console with AI test, DB stats, Gmail fetch, and system status

## Known issues / incomplete
- Tailwind CSS may need recompilation when new utility classes are added (`npx @tailwindcss/cli -i static/input.css -o static/style.css`)
- No todo/meeting extraction yet (Phase 4)
- No order extraction yet (Phase 5)
- No full analytics charts (Phase 6) — only summary stats
- All page content except email + home + settings is placeholder — will be populated in Phases 7-11
- n8n workflow is empty placeholder (Phase 12)
- `token.json` is saved to project root — it is in `.gitignore` (contains OAuth secrets)

## Environment
- Python version: 3.11+
- n8n version: latest (install via `npm install -g n8n`)
- Tailwind CSS version: 4.x via CLI (`npx @tailwindcss/cli`)
- **AI: Google Gemini** via `google-genai` SDK (FREE tier: 1,500 req/day, 1M tokens/day, no credit card)
- Key env vars required: GEMINI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI, SECRET_KEY, DATABASE_PATH
- `REDIRECT_URI` must be set to `http://localhost:8000/api/auth/callback` (in .env AND in Google Cloud Console)
- OpenAI is NOT used — all AI calls go through Gemini

## File map
```
mailmind/
├── CONTEXT.md                           — this file (project context, read every phase)
├── README.md                            — complete setup instructions for CS students
├── .env.example                         — environment variable template with comments
├── token.json                           — OAuth tokens (auto-created after /api/auth/login — DO NOT COMMIT)
├── backend/
│   ├── main.py                          — FastAPI entry point, Jinja config, routers
│   ├── config.py                        — loads env vars: GEMINI_API_KEY, AI_MODEL_FAST, AI_MODEL_DRAFT, etc.
│   ├── requirements.txt                 — pinned Python deps (google-genai, fastapi, etc. — no openai)
│   ├── db/
│   │   └── sqlite.py                    — SQLite init, 5 tables, is_processed(), mark_processed()
│   ├── routes/
│   │   ├── pages.py                     — Jinja2 template UI routes (/, /email, /crafter, /orders, /settings, /dev)
│   │   ├── auth.py                      — Gmail OAuth2: /login, /callback, /status, /logout ✅ Phase 2
│   │   ├── emails.py                    — Gmail fetch: /unread, /check, /mark-processed ✅ Phase 2
│   │   ├── pipeline.py                  — AI endpoints: /classify, /summarize, /draft, /process-email ✅ Phase 3
│   │   ├── analytics.py                 — Dashboard stats: /summary ✅ Phase 3 (full charts Phase 6)
│   │   ├── dev.py                       — Developer sandbox: /status, /db-stats, /test-ai, /emails ✅ Phase 3
│   │   ├── todos.py                     — todo CRUD placeholder (Phase 4)
│   │   ├── meetings.py                  — meetings listing placeholder (Phase 4)
│   │   └── orders.py                    — order tracking placeholder (Phase 5)
│   ├── templates/
│   │   ├── base.html                    — layout shell (sidebar + topbar + content block)
│   │   ├── home.html                    — dashboard with quick-stats + analytics bars ✅ Phase 3
│   │   ├── email.html                   — 3-pane inbox with AI pipeline integration ✅ Phase 3
│   │   ├── crafter.html                 — compose UI placeholder (Phase 9)
│   │   ├── orders.html                  — purchases UI placeholder (Phase 10)
│   │   ├── settings.html                — settings UI (Gmail card ✅ Phase 2)
│   │   └── dev.html                     — developer console ✅ Phase 3
│   ├── static/
│   │   ├── input.css                    — Tailwind theme variables
│   │   ├── style.css                    — Compiled Tailwind output
│   │   └── app.js                       — Vanilla JavaScript (sidebar active state)
│   └── pipeline/
│       ├── gemini.py                    — Shared Gemini client: call_fast(), call_draft() ✅ Phase 3
│       ├── classifier.py                — classify_email() with few-shot prompting ✅ Phase 3
│       ├── summarizer.py                — summarize_email() → headline + facts + actions ✅ Phase 3
│       ├── drafter.py                   — draft_reply() with classification/summary context ✅ Phase 3
│       ├── todo_extractor.py            — todo extraction placeholder (Phase 4)
│       ├── meeting_extractor.py         — meeting extraction placeholder (Phase 4)
│       └── order_extractor.py           — order extraction placeholder (Phase 5)
├── n8n/
│   └── workflow.json                    — empty n8n workflow placeholder (Phase 12)
```

## Next phase instructions

### Phase 4 — Todo and Meeting Extraction

**Read CONTEXT.md first**, then implement:

1. **`backend/pipeline/todo_extractor.py`** — Replace placeholder with real Gemini call:
   - `extract_todos(subject, body, sender)` — calls Gemini Flash
   - Returns dict: `{ todos: [{ title, due_date, priority, source_email_subject }] }`
   - Use the shared `call_fast()` from `pipeline/gemini.py`

2. **`backend/pipeline/meeting_extractor.py`** — Replace placeholder with real Gemini call:
   - `extract_meetings(subject, body, sender)` — calls Gemini Flash
   - Returns dict: `{ meetings: [{ title, date, time, location_or_link, attendees, source_email_subject }] }`
   - Use the shared `call_fast()` from `pipeline/gemini.py`

3. **`backend/routes/todos.py`** — Wire up todo endpoints:
   - `GET /api/todos` — returns all incomplete todos ordered by priority
   - `PATCH /api/todos/{id}/done` — marks a todo as complete
   - `POST /api/todos/extract` — accepts email fields, runs `extract_todos()`, saves to DB

4. **`backend/routes/meetings.py`** — Wire up meeting endpoints:
   - `GET /api/meetings` — returns all upcoming meetings ordered by date
   - `POST /api/meetings/extract` — accepts email fields, runs `extract_meetings()`, saves to DB

5. **Update `db/sqlite.py`** — Add helper functions:
   - `save_todo(title, due_date, priority, source_email_subject)` — inserts a todo
   - `get_todos(include_done=False)` — fetches todos
   - `mark_todo_done(todo_id)` — marks a todo as complete
   - `save_meeting(...)` — inserts a meeting
   - `get_meetings()` — fetches upcoming meetings

6. **Update CONTEXT.md** with what was built, what works, and Phase 5 instructions.

**Important notes:**
- Use `google-genai` (already in requirements.txt) — NOT OpenAI
- Use the shared `call_fast()` from `pipeline/gemini.py` for all Gemini calls
- Model: `gemini-2.5-flash` for all calls (fast, free tier, good enough)
- Every file must start with a 3-5 line comment block and every function must have a docstring
- Use `print()` for logging, no logging libraries
