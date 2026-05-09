# MailMind — Project Context

## Last updated
Phase 10 — Orders Page UI (2026-05-09)

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
  - `POST /api/process-email` — runs classify + summarize + draft + todo extraction + meeting extraction
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
  - Tasks and meetings now load live data from `/api/todos` and `/api/meetings`
- **`backend/config.py`** — Updated for Gemini:
  - `GEMINI_API_KEY` loaded from `.env`
  - `AI_MODEL_FAST = "gemini-2.5-flash"` — for classify + summarize
  - `AI_MODEL_DRAFT = "gemini-2.5-flash"` — for drafting (upgradeable to gemini-2.5-pro)
  - OpenAI references removed

### Phase 4 additions
- **`backend/pipeline/todo_extractor.py`** — Gemini todo extraction:
  - `extract_todos(subject, body, sender)` implemented using `call_fast()`
  - Output normalized to `{ todos: [{ title, due_date, priority, source_email_subject }] }`
- **`backend/pipeline/meeting_extractor.py`** — Gemini meeting extraction:
  - `extract_meetings(subject, body, sender)` implemented using `call_fast()`
  - Output normalized to `{ meetings: [{ title, date, time, location_or_link, attendees, source_email_subject }] }`
- **`backend/db/sqlite.py`** — Added todo/meeting helper functions:
  - `save_todo()`, `get_todos()`, `mark_todo_done()`
  - `save_meeting()`, `get_meetings()`
- **`backend/routes/todos.py`** — Fully implemented Phase 4 todo APIs:
  - `GET /api/todos`
  - `PATCH /api/todos/{id}/done`
  - `POST /api/todos/extract`
- **`backend/routes/meetings.py`** — Fully implemented Phase 4 meeting APIs:
  - `GET /api/meetings`
  - `POST /api/meetings/extract`
- **`backend/routes/pipeline.py`** — Integrated extraction into the email analysis flow:
  - `/api/process-email` now persists todos and meetings on first-time processing for each email ID
  - Guard added to avoid duplicate entity inserts when a processed email is re-run
- **`backend/templates/home.html`** — Home dashboard now renders live todo/meeting cards:
  - Loads tasks from `/api/todos`
  - Loads meetings from `/api/meetings`
  - Supports marking tasks complete directly from dashboard UI

### Phase 5 additions
- **`backend/pipeline/order_extractor.py`** — Gemini Flash order extraction:
  - `extract_order(subject, body, sender)` with dual retry guard
  - System prompt extracts: retailer, order_number, item_description, order_date, estimated_delivery, status, tracking_number, tracking_url, price
  - Status enum validated against known set; invalid values default to 'processing'
  - Safe default dict returned if both Gemini attempts fail
- **`backend/db/sqlite.py`** — Added order DB helper functions:
  - `save_order(...)` — inserts a new order row, returns row ID
  - `get_orders()` — returns all orders ordered by created_at DESC
  - `get_order_stats()` — computes total_orders, total_spent_estimate (parsed from price strings), orders_by_status breakdown, monthly_average
- **`backend/routes/orders.py`** — Full Phase 5 order API:
  - `GET /api/orders` — returns list of OrderItem Pydantic models
  - `GET /api/orders/stats` — returns OrderStatsResponse Pydantic model
  - `POST /api/orders/extract` — runs extractor + saves to DB, returns extracted fields + new row ID
- **`backend/routes/pipeline.py`** — Integrated order extraction:
  - `/api/process-email` now runs `extract_order()` when `is_order_email=True`
  - Order saved to DB and returned in response as `"order"` key
  - Guard prevents duplicate order inserts on re-processing

### Phase 6 additions
- **`backend/db/sqlite.py`** — Added two analytics helper functions:
  - `get_analytics_overview()` — queries `processed_emails` for total_today, spam_count, flagged_suspicious, by_category (GROUP BY), by_sender_domain (top 5 via substr/instr, rest bucketed as 'other'), hourly_volume (today only, 24h→12h label)
  - `get_analytics_security()` — computes spam_rate_percent, safe_percent, and suspicious_senders list with plain-English reason strings
- **`backend/routes/analytics.py`** — Phase 6 endpoints fully implemented:
  - `GET /api/analytics/overview` — returns OverviewResponse Pydantic model
  - `GET /api/analytics/security` — returns SecurityResponse Pydantic model
  - `GET /api/analytics/summary` — Phase 3 quick-stats preserved unchanged
  - Pydantic models: `HourlyEntry`, `OverviewResponse`, `SuspiciousSender`, `SecurityResponse`
  - Both new endpoints have safe except fallbacks returning empty payloads

### Phase 8A additions
- **`backend/templates/email.html`** — Added folder-list left pane and extended JS:
  - New `<aside id="folder-nav">` column with four folders: Important, All Mail, Drafts, Spam
  - `setFolder(folder)` function — highlights active folder, resets pagination, calls renderEmailList()
  - `filteredEmails()` extended to handle all 4 folder modes (important/all/drafts/spam)
  - `updateFolderBadges()` — live count pills on Important and All Mail buttons
  - Legacy `setTab()` now delegates to `setFolder()` keeping inbox header tabs in sync
  - Inbox list panel width reduced from w-80 to w-72 to fit 4-column layout

### Phase 8B additions
- **`backend/templates/email.html`** — Right pane AI Draft panel fully wired:
  - Primary **"Save to Gmail Drafts"** button (teal, `bookmark_add` icon) calls `POST /api/drafts/save`
  - Secondary row: **Copy**, **Regenerate** (with spinning icon during call), **Send** buttons
  - Confidence badge now shows "AI Confidence: 92%" format with green/orange/grey colour tiers
  - `saveDraftToGmail()` AJAX function with inline spinner, success/error toast, button state restore
  - `regenerateDraft()` refactored: spinning icon, confidence badge refresh, success toast on done
  - Toast notification system: `showToast(msg, type)` with `toast-in`/`toast-out` CSS keyframe animations, 3s auto-dismiss, colour-coded (success=green, error=red, info=primary)
  - `btn-save-draft` added to the list of buttons enabled after pipeline completes
- **`backend/routes/emails.py`** — Added `POST /api/drafts/save` endpoint:
  - `SaveDraftRequest` Pydantic model (to, subject, body, thread_id)
  - Calls Gmail `drafts.create()` API — saves to Drafts folder without sending
  - Preserves thread association via `threadId` when supplied

### Phase 10 additions
- **`backend/templates/orders.html`** — Fully implemented Orders page:
  - Stats row: 3 cards (Total Orders, Estimated Spent, Monthly Average) fetched from `GET /api/orders/stats`
  - Filter tabs: All / Shipped / Processing / Delivered — client-side JS filter via `setFilter()`
  - Order cards grid: retailer letter avatar (deterministic colour per first letter, 10-palette), item description, order/delivery dates, status badge (teal=shipped, orange=processing, grey=delivered, red=cancelled, pink=out-for-delivery), price (right-aligned), tracking URL button or tracking number
  - `renderCard(order)` — pure JS template function producing each card's HTML
  - `loadOrders()` — parallel `Promise.all` for `/api/orders` + `/api/orders/stats`; loading / empty / error states
  - `renderStats(stats)` — injects stat values into the three card elements
  - `/orders` page route already existed in `pages.py` — no backend changes needed

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
- **Phase 4**: Todo extraction from email content is running with Gemini Flash
- **Phase 4**: Meeting extraction from email content is running with Gemini Flash
- **Phase 4**: `/api/todos` and `/api/meetings` return live SQLite-backed data
- **Phase 4**: Home page now shows real tasks and meetings instead of placeholders
- **Phase 4**: Marking task done from dashboard updates SQLite via `PATCH /api/todos/{id}/done`
- **Phase 5**: Order extraction from email content running with Gemini Flash
- **Phase 5**: `GET /api/orders` returns all stored orders (most recent first)
- **Phase 5**: `GET /api/orders/stats` returns total_orders, total_spent_estimate, orders_by_status, monthly_average
- **Phase 5**: `POST /api/orders/extract` runs extractor + persists to DB
- **Phase 5**: `/api/process-email` automatically runs order extraction when classifier flags `is_order_email=True`
- **Phase 6**: `GET /api/analytics/overview` returns total_today, spam_count, by_category, by_sender_domain, hourly_volume from SQLite
- **Phase 6**: `GET /api/analytics/security` returns spam_rate_percent, safe_percent, suspicious_senders list
- **Phase 8A**: Email page folder nav renders Important / All Mail / Drafts / Spam with active highlight and count badges
- **Phase 8A**: Folder switching filters email list correctly (Drafts = sent replies, Spam = spam-classified emails)
- **Phase 8B**: AI Draft panel shows confidence as "AI Confidence: XX%" with colour-coded badge
- **Phase 8B**: "Save to Gmail Drafts" button saves draft via Gmail API (not sent)
- **Phase 8B**: Toast notifications (success/error/info) with CSS keyframe animations on draft actions
- **Phase 8B**: Regenerate button shows spinner icon and refreshes confidence badge on completion
- **Phase 10**: Orders page renders stats row (total orders, estimated spent, monthly average) from API
- **Phase 10**: Order cards display retailer avatar, description, dates, status badge, price, track-package link
- **Phase 10**: Filter tabs (All/Shipped/Processing/Delivered) filter cards client-side without re-fetch

## Known issues / incomplete
- Tailwind CSS may need recompilation when new utility classes are added (`npx @tailwindcss/cli -i static/input.css -o static/style.css`)
- All page content except crafter/settings pages still placeholder (Phases 9, 11)
- n8n workflow is empty placeholder (Phase 12)
- `token.json` is saved to project root — it is in `.gitignore` (contains OAuth secrets)
- orders.html page still renders placeholder content (Phase 10 will wire up the UI)

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
│   │   ├── todos.py                     — todo endpoints: list, mark done, extract ✅ Phase 4
│   │   ├── meetings.py                  — meeting endpoints: list, extract ✅ Phase 4
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
│       ├── todo_extractor.py            — Gemini todo extraction ✅ Phase 4
│       ├── meeting_extractor.py         — Gemini meeting extraction ✅ Phase 4
│       └── order_extractor.py           — Gemini order extraction ✅ Phase 5
├── n8n/
│   └── workflow.json                    — empty n8n workflow placeholder (Phase 12)
```

## Next phase instructions

### Phase 6 — Analytics and Email Stats

**Read CONTEXT.md first**, then implement:

1. **`backend/routes/analytics.py`** — Expand beyond the existing `/api/analytics/summary` stub:
   - `GET /api/analytics/overview` — returns stats from `processed_emails` table:
     `{ total_today, spam_count, flagged_suspicious, by_category, by_sender_domain, hourly_volume }`
   - `GET /api/analytics/security` — returns:
     `{ spam_rate_percent, suspicious_senders: [{email, reason}], safe_percent }`
   - All fields computed purely from SQLite — no AI calls needed

2. **`backend/templates/home.html`** — Wire the new analytics endpoints into the dashboard:
   - Replace CSS-only category bar chart with data driven by `/api/analytics/overview`
   - Add sender domain breakdown section
   - Add hourly volume section if feasible within the existing layout

3. **Update CONTEXT.md** at the end with what was built, what works, and Phase 7 instructions (Phase 7 is already done — skip its UI steps, just note it).
### Phase 5 — Order and Purchase Tracking

**Read CONTEXT.md first**, then implement:

1. **`backend/pipeline/order_extractor.py`** — Replace placeholder with Gemini extraction:
  - `extract_order(subject, body, sender)`
  - Returns structured order payload:
    `{ retailer, order_number, item_description, order_date, estimated_delivery, status, tracking_number, tracking_url, price }`
  - Use shared `call_fast()` (or dedicated draft model only if quality is insufficient)

2. **`backend/db/sqlite.py`** — Add order helper functions:
  - `save_order(...)`
  - `get_orders()`
  - `get_order_stats()` with totals/status buckets

3. **`backend/routes/orders.py`** — Implement real order APIs:
  - `GET /api/orders` — list all orders (newest first)
  - `GET /api/orders/stats` — stats card payload
  - `POST /api/orders/extract` — extract and persist order data from email payload

4. **`backend/routes/pipeline.py`** — Integrate order extraction:
  - If classifier returns `is_order_email=True`, run `extract_order()` and save result
  - Include extracted order payload in `/api/process-email` response

5. **`backend/templates/orders.html`** — Replace placeholder with live data rendering:
  - fetch `/api/orders` and `/api/orders/stats`
  - display order cards, statuses, and top stats

6. **Update CONTEXT.md** with what was built, what works, and Phase 6 instructions.
