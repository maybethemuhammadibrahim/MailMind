Here's your optimised, comprehensive prompt:

---

> # AI Email Assistant — Full Project Implementation Prompt
>
> ## Context for the AI
>
> You are building a semester project called **MailMind** — an AI-powered email assistant web application. The user has provided exact HTML mockup files that represent the precise UI they want implemented. Your job is to implement the full project in phases, treating the HTML files as the ground truth for all visual design decisions. Do not deviate from the UI shown in those files.
>
> At the start of every phase, read the file `CONTEXT.md` in the project root. At the end of every phase, update `CONTEXT.md` with what was built, what works, what is pending, and what the next phase should start with. This file is the single source of truth across all sessions — if you are resuming work, always read `CONTEXT.md` first before writing any code.
>
> ---
>
> ## Project overview
>
> **Stack:**
> - Frontend: React + Vite + Tailwind CSS
> - Backend: FastAPI (Python)
> - Automation: n8n (self-hosted)
> - LLM: OpenAI GPT-4o / GPT-4o-mini
> - Auth: Gmail OAuth2 via `google-auth-oauthlib`
> - Database: SQLite (via Python `sqlite3` — no ORM)
> - Charts: Recharts (React)
>
> **Design system:** "Chromatic Professional" — card-based layout, white space, neutral greys and whites as base, accented with Teal (`#0D9488`), Orange (`#F97316`), and Pink (`#EC4899`) for status and data. Font: Inter (Google Fonts). Border radius: 8px everywhere. Subtle box shadows on cards (`0 1px 3px rgba(0,0,0,0.08)`). All styling must exactly match the provided HTML mockup files — use those as the pixel-perfect reference.
>
> **Coding rules (apply to every file, every phase):**
> - Every file starts with a 3–5 line comment block explaining what the file does
> - Every function has a docstring explaining inputs, outputs, and purpose
> - Inline comments on every non-obvious line
> - No advanced syntax — no one-liners, no complex list comprehensions, no lambdas unless explained
> - Use `print()` for logging — no logging libraries
> - All secrets in `.env` — never hardcoded
> - All API calls wrapped in `try/except` with helpful printed error messages
> - Keep functions under 30 lines — split and comment if longer
> - Simple retry on API failure: wait 2 seconds, try once more
>
> ---
>
> ## CONTEXT.md format
>
> At the end of each phase, write or update `CONTEXT.md` in this exact format:
>
> ```markdown
> # MailMind — Project Context
>
> ## Last updated
> [Phase name and date]
>
> ## What has been built
> - [bullet list of completed files and features]
>
> ## What is working
> - [bullet list of tested, confirmed-working features]
>
> ## Known issues / incomplete
> - [bullet list of anything that needs fixing or finishing]
>
> ## Environment
> - Python version: 3.11
> - Node version: [fill in]
> - n8n version: [fill in]
> - Key env vars required: OPENAI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI, SECRET_KEY
>
> ## File map
> [list every file created so far with a one-line description]
>
> ## Next phase instructions
> [Exact instructions for what to build next, so a new session can resume without confusion]
> ```
>
> ---
>
> ## Project folder structure
>
> Create this structure before writing any code:
>
> ```
> mailmind/
> ├── CONTEXT.md                  ← read/update every phase
> ├── README.md                   ← setup instructions (written in Phase 1)
> ├── .env.example
> ├── backend/
> │   ├── main.py
> │   ├── config.py
> │   ├── requirements.txt
> │   ├── db/
> │   │   └── sqlite.py
> │   ├── routes/
> │   │   ├── auth.py             ← Gmail OAuth
> │   │   ├── emails.py           ← fetch, classify, deduplicate
> │   │   ├── pipeline.py         ← classify / summarize / draft endpoints
> │   │   ├── todos.py            ← extracted to-do items
> │   │   ├── meetings.py         ← extracted meeting events
> │   │   ├── orders.py           ← order/purchase tracking
> │   │   └── analytics.py        ← spam/source/security stats
> │   └── pipeline/
> │       ├── classifier.py
> │       ├── summarizer.py
> │       ├── drafter.py
> │       ├── todo_extractor.py
> │       ├── meeting_extractor.py
> │       └── order_extractor.py
> ├── n8n/
> │   └── workflow.json
> └── frontend/
>     ├── index.html
>     ├── vite.config.js
>     ├── tailwind.config.js
>     └── src/
>         ├── main.jsx
>         ├── App.jsx
>         ├── api/                ← all fetch calls to backend
>         │   └── index.js
>         └── pages/
>             ├── Home.jsx        ← dashboard
>             ├── Email.jsx       ← smart inbox
>             ├── Crafter.jsx     ← new email composer
>             ├── Orders.jsx      ← order tracking
>             └── Settings.jsx    ← settings
>         └── components/
>             ├── Sidebar.jsx
>             ├── TodoCard.jsx
>             ├── MeetingCard.jsx
>             ├── EmailRow.jsx
>             ├── DraftPanel.jsx
>             ├── OrderCard.jsx
>             └── AnalyticsChart.jsx
> ```
>
> ---
>
> ## Phase 1 — Setup, skeleton, and README
>
> **Goal:** Get the project running with no features yet — just the shell.
>
> Write `README.md` with complete setup instructions a CS student can follow:
> - Install Python 3.11, Node.js 18+, n8n via `npm install -g n8n`
> - Create a Google Cloud project, enable Gmail API, download OAuth credentials JSON
> - Get an OpenAI API key from `platform.openai.com`
> - Create virtual environment: `python -m venv venv` then `source venv/bin/activate` (Mac/Linux) or `venv\Scripts\activate` (Windows)
> - `pip install -r requirements.txt`
> - Copy `.env.example` to `.env` and fill in all values
> - Run backend: `uvicorn main:app --reload` from the `backend/` folder
> - Run frontend: `npm install` then `npm run dev` from the `frontend/` folder
> - Import n8n workflow: open `localhost:5678`, go to Workflows → Import → select `n8n/workflow.json`
>
> Create `.env.example`:
> ```
> OPENAI_API_KEY=        # From platform.openai.com
> GOOGLE_CLIENT_ID=      # From Google Cloud Console → Credentials
> GOOGLE_CLIENT_SECRET=  # From Google Cloud Console → Credentials
> REDIRECT_URI=http://localhost:8000/auth/callback
> SECRET_KEY=            # Any random string for session signing
> DATABASE_PATH=./mailmind.db
> ```
>
> Set up `backend/main.py` with FastAPI, CORS (allow `localhost:5173`), and register all route files as empty routers for now. Set up `frontend/src/App.jsx` with React Router — five routes: `/` (Home), `/email` (Email), `/crafter` (Crafter), `/orders` (Orders), `/settings` (Settings). Each route renders its page component with placeholder text for now. Set up `frontend/src/components/Sidebar.jsx` matching the sidebar from the HTML mockup exactly — five nav items with icons (use Lucide React), active state highlight, and the MailMind logo at top.
>
> At the end: write initial `CONTEXT.md`.
>
> ---
>
> ## Phase 2 — Gmail OAuth and email fetching
>
> **Goal:** Connect to Gmail, authenticate, and fetch real emails.
>
> In `backend/routes/auth.py`, implement:
> - `GET /auth/login` — builds Google OAuth2 URL with scopes `gmail.readonly` and `gmail.modify`, redirects user to Google. Comment: explain what OAuth2 is and what scopes mean
> - `GET /auth/callback` — exchanges auth code for access + refresh tokens, saves refresh token to `.env`. Comment: explain why we save the refresh token (so user stays logged in)
>
> In `backend/routes/emails.py`, implement:
> - `GET /emails/unread` — fetches unread emails from last 24 hours via Gmail API (`google-api-python-client`). Returns list of dicts: `{ id, subject, sender, sender_email, body_plain, thread_id, timestamp }`. Comments on every Gmail API call explaining what it does
>
> In `backend/db/sqlite.py`, create the SQLite database and this table:
> ```sql
> CREATE TABLE IF NOT EXISTS processed_emails (
>     email_id TEXT PRIMARY KEY,
>     subject TEXT,
>     category TEXT,
>     priority_score INTEGER,
>     processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
> )
> ```
> Write `is_processed(email_id)` and `mark_processed(email_id, subject, category, priority_score)` with full docstrings. Comment explaining why deduplication matters for a polling system.
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 3 — AI pipeline (classifier, summarizer, drafter)
>
> **Goal:** Build the three-stage LLM pipeline as standalone Python functions, then expose them as FastAPI endpoints.
>
> All three files go in `backend/pipeline/`. Use `openai.chat.completions.create()` — synchronous, no streaming. Every call uses JSON mode (`response_format={"type": "json_object"}`). Wrap in `try/except`. On failure print a clear error and return a safe default dict. Simple retry: if first call fails, wait 2 seconds and try once more.
>
> **`classifier.py`** — function `classify_email(subject, sender, body)`:
>
> Model: `gpt-4o-mini`. System prompt: *"You are an email classification system. Think step by step about how urgent this email is before assigning a score. Return ONLY valid JSON with: category (one of: urgent, action-required, meeting-request, order-update, newsletter, spam, fyi), priority_score (integer 1–10), requires_reply (boolean), is_spam (boolean), is_order_email (boolean), action_items (list of strings)."*
>
> Include 4 few-shot examples in the user message: one urgent, one newsletter, one order email, one spam. Comment explaining what few-shot prompting is.
>
> **`summarizer.py`** — function `summarize_email(subject, body)`:
>
> Model: `gpt-4o-mini`. System prompt: *"You are a professional email summarizer. Be factual. No opinions. Return ONLY valid JSON with: one_line_summary (max 20 words), key_facts (list of up to 5 strings), action_items (list of strings)."*
>
> **`drafter.py`** — function `draft_reply(subject, body, classification, summary)`:
>
> Model: `gpt-4o`. System prompt: *"You are drafting a professional email reply. Use the classification and summary to understand what the email needs. Be concise and direct. Return ONLY valid JSON with: draft_reply (full reply text ready to send), confidence_score (float 0.0–1.0), suggested_subject (reply subject line)."* Include 3 hardcoded few-shot sent-email examples with a comment saying these should later be pulled from the user's actual sent folder.
>
> Expose all three in `backend/routes/pipeline.py` as `POST /classify`, `POST /summarize`, `POST /draft`. Add a `POST /process-email` convenience endpoint that runs all three stages in sequence and returns a combined result. Use Pydantic models for all request and response bodies — comment explaining what Pydantic does.
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 4 — Todo and meeting extraction
>
> **Goal:** Extract structured to-do items and meeting events from emails using GPT.
>
> **`pipeline/todo_extractor.py`** — function `extract_todos(subject, body, sender)`:
>
> Model: `gpt-4o-mini`. System prompt: *"Extract actionable to-do items from this email. Return ONLY valid JSON with: todos (list of objects, each with: title (string, max 10 words), due_date (string like 'Friday' or 'June 15' or null if not mentioned), priority (high/medium/low), source_email_subject (string))."*
>
> **`pipeline/meeting_extractor.py`** — function `extract_meetings(subject, body, sender)`:
>
> Model: `gpt-4o-mini`. System prompt: *"Extract any meeting, call, or calendar event mentioned in this email. Return ONLY valid JSON with: meetings (list of objects, each with: title (string), date (string or null), time (string or null), location_or_link (string or null), attendees (list of strings), source_email_subject (string)). Return an empty list if no meeting is mentioned."*
>
> Create a SQLite table for each in `db/sqlite.py`:
>
> ```sql
> CREATE TABLE IF NOT EXISTS todos (
>     id INTEGER PRIMARY KEY AUTOINCREMENT,
>     title TEXT,
>     due_date TEXT,
>     priority TEXT,
>     source_email_subject TEXT,
>     is_done INTEGER DEFAULT 0,
>     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
> )
>
> CREATE TABLE IF NOT EXISTS meetings (
>     id INTEGER PRIMARY KEY AUTOINCREMENT,
>     title TEXT,
>     date TEXT,
>     time TEXT,
>     location_or_link TEXT,
>     attendees TEXT,
>     source_email_subject TEXT,
>     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
> )
> ```
>
> In `backend/routes/todos.py`, create:
> - `GET /todos` — returns all incomplete todos ordered by priority
> - `PATCH /todos/{id}/done` — marks a todo as complete
>
> In `backend/routes/meetings.py`, create:
> - `GET /meetings` — returns all upcoming meetings ordered by date
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 5 — Order and purchase tracking
>
> **Goal:** Detect order/shipping emails and extract structured purchase data.
>
> **`pipeline/order_extractor.py`** — function `extract_order(subject, body, sender)`:
>
> Model: `gpt-4o-mini`. Only call this if the classifier returned `is_order_email: true`. System prompt: *"You are extracting order and purchase information from an email. Return ONLY valid JSON with: retailer (string), order_number (string or null), item_description (string, max 15 words), order_date (string or null), estimated_delivery (string or null), status (one of: ordered, processing, shipped, out-for-delivery, delivered, cancelled), tracking_number (string or null), tracking_url (string or null), price (string or null, include currency symbol)."*
>
> Create a SQLite table:
> ```sql
> CREATE TABLE IF NOT EXISTS orders (
>     id INTEGER PRIMARY KEY AUTOINCREMENT,
>     retailer TEXT,
>     order_number TEXT,
>     item_description TEXT,
>     order_date TEXT,
>     estimated_delivery TEXT,
>     status TEXT,
>     tracking_number TEXT,
>     tracking_url TEXT,
>     price TEXT,
>     source_email_id TEXT,
>     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
> )
> ```
>
> In `backend/routes/orders.py`, create:
> - `GET /orders` — returns all orders, most recent first
> - `GET /orders/stats` — returns: `{ total_orders, total_spent_estimate, orders_by_status: { shipped: N, delivered: N, processing: N }, monthly_average }`
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 6 — Analytics and email stats
>
> **Goal:** Generate the data for the home page analytics charts.
>
> In `backend/routes/analytics.py`, create:
>
> - `GET /analytics/overview` — returns stats computed from the `processed_emails` table:
>   ```json
>   {
>     "total_today": 24,
>     "spam_count": 3,
>     "flagged_suspicious": 1,
>     "by_category": { "urgent": 2, "action-required": 5, "newsletter": 8, "fyi": 6, "spam": 3 },
>     "by_sender_domain": { "gmail.com": 12, "outlook.com": 5, "amazon.com": 4, "other": 3 },
>     "hourly_volume": [{ "hour": "8am", "count": 3 }, ...]
>   }
>   ```
>   Comment explaining how to compute each field from the database.
>
> - `GET /analytics/security` — returns:
>   ```json
>   {
>     "spam_rate_percent": 12.5,
>     "suspicious_senders": [ { "email": "...", "reason": "..." } ],
>     "safe_percent": 87.5
>   }
>   ```
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 7 — Frontend: Home page (dashboard)
>
> **Goal:** Build the Home page exactly matching the provided HTML mockup.
>
> The home page has two columns:
>
> **Left column — Todo section:**
> `TodoCard.jsx` component. Fetches from `GET /todos`. Each todo renders as a card with: checkbox (clicking calls `PATCH /todos/{id}/done` and removes it from list), title text, due date in muted text, a priority dot (red = high, orange = medium, gray = low). Add a "source" line showing which email it came from in small muted text. Empty state: "No tasks yet — MailMind will extract to-dos from your emails automatically." Match card styling exactly from the mockup: 8px border radius, subtle shadow, white background.
>
> **Right column — Meetings section:**
> `MeetingCard.jsx` component. Fetches from `GET /meetings`. Each meeting card shows: meeting title, date + time row with a calendar icon, location or video link with a link icon (make it clickable), attendees as small avatar initials circles, source email in muted text. Match the card layout from the mockup exactly.
>
> **Bottom — Analytics section:**
> `AnalyticsChart.jsx` component. Uses Recharts. Fetches from `GET /analytics/overview` and `GET /analytics/security`.
>
> Render three charts:
> 1. A donut/pie chart of emails by category — use the Teal/Orange/Pink/Grey palette from the design system
> 2. A bar chart of emails by sender domain (top 5 sources)
> 3. A security summary card — shows spam rate as a large number, a horizontal bar split between "Safe" (teal) and "Suspicious/Spam" (orange+red), and a list of flagged senders if any
>
> Add a top stats bar with three metric tiles: "Emails today", "Tasks pending", "Meetings this week" — match the card style from the mockup.
>
> Comment every component explaining what it renders and which endpoint it calls.
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 8 — Frontend: Email page (smart inbox)
>
> **Goal:** Build the Email page — three-pane interface matching the HTML mockup.
>
> **Left pane — folder list:** "Important", "All Mail", "Drafts", "Spam". Clicking a folder filters the email list. Active folder highlighted in teal.
>
> **Center pane — email list:** Fetches from `GET /emails/unread`. Each row uses `EmailRow.jsx`: sender avatar (initials circle), sender name + subject bold, one-line AI summary below in muted grey, timestamp right-aligned, priority badge (color-coded pill). Clicking a row loads it in the right pane. "Important" filter shows only emails with `priority_score >= 7`.
>
> **Right pane — email detail + draft:** Shows full subject, sender info, email body in a scrollable card. Below it, the AI Draft panel using `DraftPanel.jsx`: light teal-tinted background card, "AI Draft" label with a small sparkle icon, the draft text in an editable `<textarea>`, confidence score as a percentage, two buttons: "Save to Gmail Drafts" (calls `POST /drafts/save` — write this endpoint too) and "Regenerate" (calls `POST /draft` again and refreshes). Match styling from mockup exactly.
>
> Add a loading spinner while the AI pipeline runs. Add an error message if the pipeline fails.
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 9 — Frontend: AI Email Crafter
>
> **Goal:** Build the new email composer page matching the HTML mockup.
>
> The crafter page is a distraction-free composition view. Layout: centered card, max-width 720px.
>
> **Fields:**
> - To (text input with email validation)
> - Subject (text input)
> - Prompt / intent (textarea — the user describes what they want to say, not the full email)
>
> **Tone selector:** Four toggle buttons — Professional, Casual, Direct, Persuasive. Only one active at a time. Active state: teal background, white text.
>
> **Quick prompt chips:** Small pill buttons for common scenarios — "Follow Up", "Polite Decline", "Meeting Request", "Thank You", "Apology". Clicking a chip pre-fills the prompt field with a starter text. Comment explaining this is a UX shortcut.
>
> **Generate button:** Calls `POST /crafter/generate` (write this FastAPI endpoint — it calls GPT-4o with the tone, prompt, recipient, and subject as context and returns `{ generated_email, subject_suggestion }`). Show the result in an editable textarea below. Add a "Send via Gmail" button that calls `POST /crafter/send`.
>
> Match all styling from the mockup. Comment each component.
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 10 — Frontend: Orders page
>
> **Goal:** Build the orders and purchase tracking page matching the HTML mockup.
>
> **Top stats row:** Three metric cards — "Total Orders This Year", "Estimated Total Spent", "Monthly Average". Fetch from `GET /orders/stats`. Match card styling from mockup.
>
> **Order cards grid:** Fetches from `GET /orders`. Each `OrderCard.jsx` shows:
> - Retailer name + logo placeholder (first letter of retailer in a colored circle)
> - Item description (bold)
> - Order date and estimated delivery date
> - Status badge — color coded: Shipped = teal, Processing = orange, Delivered = grey, Cancelled = red, Out for Delivery = pink
> - Price right-aligned
> - Tracking number in monospace if available
> - "Track Package" button if `tracking_url` is present — opens in new tab
>
> **Filter tabs:** "All", "Shipped", "Processing", "Delivered" — clicking filters the grid client-side (no new API call — just filter the already-fetched data in React state). Comment explaining why client-side filtering is fine for small datasets.
>
> Match all styling from the mockup. Comment each component.
>
> Update `CONTEXT.md`.
>
> ---
>
> ## Phase 11 — Frontend: Settings page
>
> **Goal:** Build the settings page matching the HTML mockup.
>
> Organise settings into three sections as cards:
>
> **AI Personality:**
> - Tone of Voice slider — five steps: Very Formal → Formal → Balanced → Casual → Very Casual. Show current value as a label. Save to `PATCH /settings/ai`
> - Drafting sensitivity toggle — "Always draft" / "Draft for important only" / "Never auto-draft"
> - Writing style checkboxes — "Use bullet points", "Keep replies short", "Always include greeting/sign-off"
>
> **Account & Connections:**
> - Connected Gmail account — show the connected email address (fetch from `GET /settings`), a green "Connected" badge, and a "Disconnect" button
> - "Connect Gmail" button if not connected — links to `/auth/login`
>
> **Security:**
> - Two-Factor Authentication toggle — show enabled/disabled state, a "Set up 2FA" button (placeholder — just shows a coming soon toast)
> - "Change Password" button (placeholder toast)
> - "Delete all processed data" button — calls `DELETE /settings/data` which wipes the SQLite database. Show a confirmation dialog before allowing this. Style the button in red as a danger action.
>
> Create `GET /settings` and `PATCH /settings/ai` and `DELETE /settings/data` in a new `backend/routes/settings.py`. Settings are stored as a `settings` table in SQLite with key-value pairs.
>
> Match all styling from the mockup. Update `CONTEXT.md`.
>
> ---
>
> ## Phase 12 — n8n workflow
>
> **Goal:** Wire up the full automation pipeline in n8n.
>
> Generate `n8n/workflow.json` that implements:
>
> 1. Gmail Trigger — polls every 15 minutes for new unread emails
> 2. HTTP Request → `POST /process-email` on the FastAPI backend (runs classify + summarize + draft)
> 3. Code node — checks `is_processed` by calling `GET /emails/check/{id}`. Skip if already done
> 4. IF node — `category == "newsletter"` or `category == "spam"` → auto-archive branch
> 5. IF node — `is_order_email == true` → HTTP Request → `POST /orders/extract`
> 6. HTTP Request → `POST /todos/extract` (runs todo extractor)
> 7. HTTP Request → `POST /meetings/extract` (runs meeting extractor)
> 8. IF node — `priority_score >= 8` → Slack node (optional, commented out by default)
> 9. Gmail Draft node — saves draft with `[AI Draft]` prefix
> 10. HTTP Request → `POST /emails/mark-processed`
>
> Second workflow — Cron at 7:00 AM daily:
> - Calls `GET /analytics/overview` and `GET /todos`
> - Formats a digest message
> - Slack node posts digest (optional, commented out by default)
>
> Add a sticky note node in n8n explaining what each node does and how to configure credentials.
>
> Update `CONTEXT.md` with final project status and complete file map.
>
> ---
>
> ## Final deliverable checklist (add to README)
>
> ```
> Phase 1  - [ ] Project runs, sidebar navigation works, all pages load
> Phase 2  - [ ] Gmail OAuth login works, unread emails fetched
> Phase 3  - [ ] Classify / summarize / draft pipeline returns correct JSON
> Phase 4  - [ ] Todos and meetings extracted and stored in SQLite
> Phase 5  - [ ] Order emails detected and structured data stored
> Phase 6  - [ ] Analytics endpoint returns correct stats
> Phase 7  - [ ] Home page renders todos, meetings, charts from live data
> Phase 8  - [ ] Email page shows inbox, clicking email shows AI draft
> Phase 9  - [ ] Crafter generates full email from tone + prompt
> Phase 10 - [ ] Orders page shows all orders with correct status badges
> Phase 11 - [ ] Settings saved to DB, Gmail connected/disconnected works
> Phase 12 - [ ] n8n workflow runs end-to-end, Gmail Draft appears in inbox
> ```