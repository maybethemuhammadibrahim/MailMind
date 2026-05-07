# MailMind — Project Context

## Last updated
Phase 1 — Migration to Jinja2 Monolith (2026-05-07)

## What has been built
- Project directory structure configured for a FastAPI + Jinja2 monolith
- Backend: FastAPI app with CORS, UI pages router (`routes/pages.py`), and 7 API route modules prefixed with `/api`
- Backend: 6 pipeline modules (all with placeholder functions and full docstrings)
- Backend: SQLite database module with 5 tables (processed_emails, todos, meetings, orders, settings) and deduplication helpers
- Backend: `config.py` loading env vars from `.env` via python-dotenv
- Backend: `requirements.txt` with pinned Python dependencies (including `jinja2`)
- Frontend/UI: Jinja2 templates (`base.html`, `home.html`, `email.html`, `crafter.html`, `orders.html`, `settings.html`) replacing React components
- Frontend/UI: Tailwind v4 integration via standalone CLI. `@theme` definitions in `static/input.css`
- Frontend/UI: Vanilla JS inside `static/app.js` for interactivity and active link management
- Root: `README.md` with complete setup instructions
- Root: `.env.example` with all required env vars
- Root: `n8n/workflow.json` placeholder

## What is working
- Backend: All pages are routable via FastAPI Jinja2 template responses
- Frontend: Sidebar navigation shows correct active state per route via Vanilla JS
- Frontend: All pages render their mockup-matched layout shells with placeholder content via template inheritance
- Backend: All route modules are importable and registered in `main.py`
- Backend: All pipeline modules have placeholder functions returning safe defaults
- Backend: SQLite module can create all 5 tables

## Known issues / incomplete
- Tailwind CSS needs to be compiled using the npx command
- No actual Gmail OAuth flow implemented (Phase 2)
- No OpenAI API calls implemented (Phase 3)
- No live data connections between UI and APIs
- All page content is placeholder — will be populated in Phases 7-11
- n8n workflow is empty placeholder (Phase 12)

## Environment
- Python version: 3.11+
- n8n version: latest (install via `npm install -g n8n`)
- Tailwind CSS version: 4.x via CLI (`npx @tailwindcss/cli`)
- Key env vars required: OPENAI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI, SECRET_KEY, DATABASE_PATH

## File map
```
mailmind/
├── CONTEXT.md                           — this file (project context, read every phase)
├── README.md                            — complete setup instructions for CS students
├── .env.example                         — environment variable template with comments
├── backend/
│   ├── main.py                          — FastAPI entry point, Jinja config, routers
│   ├── config.py                        — loads env vars from .env via python-dotenv
│   ├── requirements.txt                 — pinned Python dependencies
│   ├── db/
│   │   └── sqlite.py                    — SQLite init, 5 tables, is_processed(), mark_processed()
│   ├── routes/
│   │   ├── pages.py                     — Jinja2 template UI routes
│   │   ├── auth.py                      — Gmail OAuth placeholder (Phase 2)
│   │   ├── emails.py                    — email fetching placeholder (Phase 2)
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
│   │   └── settings.html                — settings UI
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

### Phase 2 — Gmail OAuth and Email Fetching

**Read CONTEXT.md first**, then implement:

1. **`backend/routes/auth.py`** — Replace placeholders with real Gmail OAuth2 flow:
   - `GET /api/auth/login` — build Google OAuth2 URL with scopes `gmail.readonly` and `gmail.modify`, redirect to Google
   - `GET /api/auth/callback` — exchange auth code for access + refresh tokens, save refresh token to .env
   - Add inline comments explaining OAuth2, scopes, and why we save the refresh token

2. **`backend/routes/emails.py`** — Replace placeholders with real Gmail API calls:
   - `GET /api/emails/unread` — fetch unread emails from last 24h via `google-api-python-client`
   - Return list of dicts: `{ id, subject, sender, sender_email, body_plain, thread_id, timestamp }`
   - Add comments on every Gmail API call explaining what it does

3. **`backend/db/sqlite.py`** — Already has the `processed_emails` table and helpers. Verify they work with the auth flow.

4. **Wrap all API calls in try/except** with clear error messages. Use simple retry on failure (wait 2s, try once more).

5. **Update CONTEXT.md** with what was built, what works, and Phase 3 instructions.

**Important notes for the implementing session:**
- The Tailwind version is v4 (not v3) — configuration is done via `@theme` in `static/input.css`. Compile with `npx @tailwindcss/cli -i ./backend/static/input.css -o ./backend/static/style.css --watch`
- The backend uses `python-dotenv` to load `.env` — the file should be at `mailmind/.env`
- All pipeline functions in `backend/pipeline/` already have full docstrings — fill in the actual implementations starting Phase 3
- Every file must start with a 3-5 line comment block and every function must have a docstring
- Use `print()` for logging, no logging libraries
- Keep functions under 30 lines

