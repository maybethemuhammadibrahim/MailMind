# backend/db/sqlite.py
# ---------------------------------------------------------------
# Handles all SQLite database operations for MailMind. Creates
# tables on first run and provides helper functions for CRUD
# operations on emails, pipeline results, todos, meetings, orders.
# ---------------------------------------------------------------

import json
import sqlite3

# Import the database path from our central config
from config import DATABASE_PATH


def get_connection():
    """
    Opens a connection to the SQLite database file.

    Returns:
        sqlite3.Connection: an open database connection with
                            row_factory set to sqlite3.Row so
                            results can be accessed by column name.
    """
    # Connect to the database file specified in .env
    connection = sqlite3.connect(DATABASE_PATH)

    # This lets us access columns by name (e.g. row["subject"])
    # instead of by index (e.g. row[1])
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """
    Creates all required tables if they don't already exist.
    Called once when the app starts up. Each table is created
    with IF NOT EXISTS so it's safe to call multiple times.

    Tables created:
        - emails: full email content + cached AI pipeline results
        - processed_emails: tracks which emails have been processed
        - todos: to-do items extracted from emails
        - meetings: meeting events extracted from emails
        - orders: order/purchase data extracted from emails
        - settings: key-value store for user preferences
    """
    connection = get_connection()
    cursor = connection.cursor()

    # --- Emails ---
    # Stores the full content of fetched Gmail messages so the email
    # page can load instantly from DB instead of hitting the Gmail API
    # on every visit. Also caches AI pipeline results (classification,
    # summary, draft) so they persist across page reloads and are only
    # regenerated when the user explicitly clicks "Regenerate".
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            email_id        TEXT PRIMARY KEY,
            subject         TEXT,
            sender          TEXT,
            sender_email    TEXT,
            body_plain      TEXT,
            thread_id       TEXT,
            timestamp       TEXT,
            is_sent         INTEGER DEFAULT 0,
            classification  TEXT,
            summary         TEXT,
            draft_reply     TEXT,
            draft_confidence REAL,
            draft_subject   TEXT,
            fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration guard for existing databases created before is_sent existed.
    cursor.execute("PRAGMA table_info(emails)")
    email_columns = [row[1] for row in cursor.fetchall()]
    if "is_sent" not in email_columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN is_sent INTEGER DEFAULT 0")

    # --- Processed Emails ---
    # Tracks which emails have already been through the AI pipeline
    # so we don't process the same email twice (deduplication).
    # This is important because n8n polls Gmail every 15 minutes,
    # and the same email could appear in multiple poll results.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            email_id TEXT PRIMARY KEY,
            subject TEXT,
            sender TEXT,
            category TEXT,
            priority_score INTEGER,
            is_spam INTEGER DEFAULT 0,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Todos ---
    # Stores actionable to-do items extracted from emails by GPT.
    # is_done tracks whether the user has checked it off.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            due_date TEXT,
            priority TEXT,
            source_email_subject TEXT,
            is_done INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Meetings ---
    # Stores meeting/call/event data extracted from emails.
    # attendees is stored as a comma-separated string for simplicity.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            time TEXT,
            location_or_link TEXT,
            attendees TEXT,
            source_email_subject TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Orders ---
    # Stores order/purchase information extracted from shipping
    # and order confirmation emails.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer TEXT,
            order_number TEXT,
            item_description TEXT,
            order_date TEXT,
            estimated_delivery TEXT,
            status TEXT,
            tracking_number TEXT,
            tracking_url TEXT,
            price TEXT,
            source_email_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Settings ---
    # Simple key-value store for user preferences (tone, auto-draft, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Save all table creations to disk
    connection.commit()
    connection.close()

    print("[DB] All tables initialized successfully.")


def is_processed(email_id):
    """
    Checks whether an email has already been processed by the
    AI pipeline. Used for deduplication when polling Gmail.

    Args:
        email_id (str): the unique Gmail message ID

    Returns:
        bool: True if the email is already in the database
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Look for this email_id in the processed_emails table
    cursor.execute(
        "SELECT 1 FROM processed_emails WHERE email_id = ?",
        (email_id,)
    )
    result = cursor.fetchone()
    connection.close()

    # If we found a row, the email has been processed
    return result is not None


def mark_processed(email_id, subject, sender, category, priority_score, is_spam=False):
    """
    Records an email as processed so it won't be run through the
    AI pipeline again on the next poll.

    Args:
        email_id (str): the unique Gmail message ID
        subject (str): the email subject line
        sender (str): the sender's email address
        category (str): the classification category (e.g. "urgent")
        priority_score (int): priority score from 1-10
        is_spam (bool): whether the email was classified as spam
    """
    connection = get_connection()
    cursor = connection.cursor()

    # INSERT OR REPLACE handles the case where the email_id
    # already exists (shouldn't happen, but safe to handle)
    cursor.execute(
        """INSERT OR REPLACE INTO processed_emails
           (email_id, subject, sender, category, priority_score, is_spam)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (email_id, subject, sender, category, priority_score, int(is_spam))
    )

    connection.commit()
    connection.close()


# ---------------------------------------------------------------------------
# Email storage helpers — used by the email page for instant loads
# ---------------------------------------------------------------------------


def save_email(email_dict):
    """
    Saves a fetched Gmail message to the emails table.

    Uses INSERT OR IGNORE so that re-syncing the same email does NOT
    overwrite any AI results (classification, summary, draft) that
    were already stored from a previous pipeline run.

    Args:
        email_dict (dict): keys must include email_id, subject, sender,
                           sender_email, body_plain, thread_id, timestamp
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Accept either "id" (Gmail payload shape) or "email_id" keys.
    email_id = email_dict.get("id") or email_dict.get("email_id")
    if not email_id:
        raise ValueError("save_email requires 'id' or 'email_id'")

    # Upsert core email fields while preserving cached AI columns.
    # We intentionally do not touch classification/summary/draft here.
    cursor.execute(
        """INSERT INTO emails
           (email_id, subject, sender, sender_email, body_plain, thread_id, timestamp, is_sent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(email_id) DO UPDATE SET
             subject=excluded.subject,
             sender=excluded.sender,
             sender_email=excluded.sender_email,
             body_plain=excluded.body_plain,
             thread_id=excluded.thread_id,
             timestamp=excluded.timestamp,
             is_sent=excluded.is_sent""",
        (
            email_id,
            email_dict.get("subject", ""),
            email_dict.get("sender", ""),
            email_dict.get("sender_email", ""),
            email_dict.get("body_plain", ""),
            email_dict.get("thread_id", ""),
            email_dict.get("timestamp", ""),
            int(bool(email_dict.get("is_sent", False))),
        ),
    )

    connection.commit()
    connection.close()


def get_recent_emails(limit=5):
    """
    Returns the most recent emails from the local database.

    Each row is converted to a dict with nested classification,
    summary, and draft objects parsed from their JSON strings.

    Args:
        limit (int): maximum number of emails to return (default 5)

    Returns:
        list[dict]: emails ordered by timestamp descending
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM emails ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    connection.close()

    emails = []
    for row in rows:
        email = {
            "id": row["email_id"],
            "subject": row["subject"],
            "sender": row["sender"],
            "sender_email": row["sender_email"],
            "body_plain": row["body_plain"],
            "thread_id": row["thread_id"],
            "timestamp": row["timestamp"],
            "is_sent": bool(row["is_sent"]) if "is_sent" in row.keys() else False,
        }

        # Parse cached AI results if they exist
        # classification and summary are stored as JSON strings
        if row["classification"]:
            try:
                email["classification"] = json.loads(row["classification"])
            except (json.JSONDecodeError, TypeError):
                email["classification"] = None
        else:
            email["classification"] = None

        if row["summary"]:
            try:
                email["summary"] = json.loads(row["summary"])
            except (json.JSONDecodeError, TypeError):
                email["summary"] = None
        else:
            email["summary"] = None

        # Draft fields are plain values, not JSON
        if row["draft_reply"]:
            email["draft"] = {
                "draft_reply": row["draft_reply"],
                "confidence_score": row["draft_confidence"],
                "suggested_subject": row["draft_subject"],
            }
        else:
            email["draft"] = None

        emails.append(email)

    return emails


def get_email(email_id):
    """
    Fetches a single email by its Gmail message ID.

    Args:
        email_id (str): the Gmail message ID

    Returns:
        dict | None: the email row as a dict, or None if not found
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM emails WHERE email_id = ?", (email_id,))
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)


def save_pipeline_result(email_id, classification, summary, draft):
    """
    Persists the full AI pipeline output (classify + summarize + draft)
    to the emails table so results survive page reloads.

    Args:
        email_id       (str):  Gmail message ID
        classification (dict): output from classify_email()
        summary        (dict): output from summarize_email()
        draft          (dict): output from draft_reply()
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """UPDATE emails
           SET classification = ?, summary = ?,
               draft_reply = ?, draft_confidence = ?, draft_subject = ?
           WHERE email_id = ?""",
        (
            json.dumps(classification),
            json.dumps(summary),
            draft.get("draft_reply", ""),
            draft.get("confidence_score", 0.5),
            draft.get("suggested_subject", ""),
            email_id,
        ),
    )

    connection.commit()
    connection.close()
    print(f"[DB] Saved pipeline results for {email_id}")


def save_draft(email_id, draft_reply, confidence, subject):
    """
    Overwrites only the draft columns for an email. Called when
    the user clicks "Regenerate" — updates the cached draft
    without re-running classification or summarization.

    Args:
        email_id    (str):   Gmail message ID
        draft_reply (str):   the new draft text
        confidence  (float): confidence score 0.0-1.0
        subject     (str):   suggested reply subject line
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """UPDATE emails
           SET draft_reply = ?, draft_confidence = ?, draft_subject = ?
           WHERE email_id = ?""",
        (draft_reply, confidence, subject, email_id),
    )

    connection.commit()
    connection.close()
    print(f"[DB] Updated draft for {email_id}")


# ---------------------------------------------------------------------------
# Todo helpers
# ---------------------------------------------------------------------------


def save_todo(title, due_date, priority, source_email_subject):
    """
    Inserts a single todo item extracted from an email.

    Args:
        title (str): todo title text
        due_date (str | None): extracted due date or None
        priority (str): one of high/medium/low
        source_email_subject (str): source email subject for traceability

    Returns:
        int: newly created todo row ID
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """INSERT INTO todos (title, due_date, priority, source_email_subject)
           VALUES (?, ?, ?, ?)""",
        (title, due_date, priority, source_email_subject),
    )

    todo_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return todo_id


def get_todos(include_done=False):
    """
    Fetches todos ordered by priority and creation time.

    Args:
        include_done (bool): whether completed todos are included

    Returns:
        list[dict]: todo rows in API-ready format
    """
    connection = get_connection()
    cursor = connection.cursor()

    where_clause = "" if include_done else "WHERE is_done = 0"
    cursor.execute(
        f"""SELECT * FROM todos
            {where_clause}
            ORDER BY
              CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
              END,
              created_at DESC"""
    )

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "due_date": row["due_date"],
            "priority": row["priority"],
            "source_email_subject": row["source_email_subject"],
            "is_done": bool(row["is_done"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def mark_todo_done(todo_id):
    """
    Marks one todo item as completed.

    Args:
        todo_id (int): todo row ID

    Returns:
        bool: True if a row was updated
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("UPDATE todos SET is_done = 1 WHERE id = ?", (todo_id,))

    updated = cursor.rowcount > 0
    connection.commit()
    connection.close()
    return updated


# ---------------------------------------------------------------------------
# Meeting helpers
# ---------------------------------------------------------------------------


def save_meeting(
    title,
    date,
    time,
    location_or_link,
    attendees,
    source_email_subject,
):
    """
    Inserts a single meeting event extracted from an email.

    Args:
        title (str): meeting title
        date (str | None): extracted date
        time (str | None): extracted time
        location_or_link (str | None): location or meeting URL
        attendees (list[str]): attendee names/emails
        source_email_subject (str): source email subject for traceability

    Returns:
        int: newly created meeting row ID
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """INSERT INTO meetings
           (title, date, time, location_or_link, attendees, source_email_subject)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            title,
            date,
            time,
            location_or_link,
            json.dumps(attendees or []),
            source_email_subject,
        ),
    )

    meeting_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return meeting_id


def get_meetings():
    """
    Fetches meetings ordered by date, then time, then creation time.

    Returns:
        list[dict]: meeting rows in API-ready format
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """SELECT * FROM meetings
           ORDER BY
             CASE WHEN date IS NULL OR date = '' THEN 1 ELSE 0 END,
             date ASC,
             CASE WHEN time IS NULL OR time = '' THEN 1 ELSE 0 END,
             time ASC,
             created_at DESC"""
    )

    rows = cursor.fetchall()
    connection.close()

    meetings = []
    for row in rows:
        attendees = []
        if row["attendees"]:
            try:
                parsed = json.loads(row["attendees"])
                if isinstance(parsed, list):
                    attendees = [str(a) for a in parsed if str(a).strip()]
            except (TypeError, json.JSONDecodeError):
                attendees = []

        meetings.append(
            {
                "id": row["id"],
                "title": row["title"],
                "date": row["date"],
                "time": row["time"],
                "location_or_link": row["location_or_link"],
                "attendees": attendees,
                "source_email_subject": row["source_email_subject"],
                "created_at": row["created_at"],
            }
        )

    return meetings


# ---------------------------------------------------------------------------
# Order helpers
# ---------------------------------------------------------------------------


def save_order(
    retailer,
    order_number,
    item_description,
    order_date,
    estimated_delivery,
    status,
    tracking_number,
    tracking_url,
    price,
    source_email_id,
):
    """
    Inserts a single order extracted from an email into the orders table.

    Args:
        retailer          (str):       store or brand name
        order_number      (str|None):  order reference number
        item_description  (str):       short description of items ordered
        order_date        (str|None):  date the order was placed
        estimated_delivery(str|None):  expected delivery date
        status            (str):       one of ordered/processing/shipped/
                                       out-for-delivery/delivered/cancelled
        tracking_number   (str|None):  carrier tracking number
        tracking_url      (str|None):  direct link to tracking page
        price             (str|None):  total price including currency symbol
        source_email_id   (str):       Gmail message ID this order came from

    Returns:
        int: newly created order row ID
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """INSERT INTO orders
           (retailer, order_number, item_description, order_date,
            estimated_delivery, status, tracking_number, tracking_url,
            price, source_email_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            retailer,
            order_number,
            item_description,
            order_date,
            estimated_delivery,
            status,
            tracking_number,
            tracking_url,
            price,
            source_email_id,
        ),
    )

    order_id = cursor.lastrowid
    connection.commit()
    connection.close()
    print(f"[DB] Saved order id={order_id} retailer='{retailer}'")
    return order_id


def get_orders():
    """
    Returns all orders sorted by creation time (most recent first).

    Returns:
        list[dict]: all order rows in API-ready format
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Most recent first — newest order appears at the top of the list
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")

    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "id":                 row["id"],
            "retailer":           row["retailer"],
            "order_number":       row["order_number"],
            "item_description":   row["item_description"],
            "order_date":         row["order_date"],
            "estimated_delivery": row["estimated_delivery"],
            "status":             row["status"],
            "tracking_number":    row["tracking_number"],
            "tracking_url":       row["tracking_url"],
            "price":              row["price"],
            "source_email_id":    row["source_email_id"],
            "created_at":         row["created_at"],
        }
        for row in rows
    ]


def get_order_stats():
    """
    Computes aggregate statistics across all stored orders.

    Calculates:
        - total_orders:         total row count in orders table
        - orders_by_status:     count per status value
        - total_spent_estimate: sum of numeric price values that could be parsed
        - monthly_average:      total_spent divided by number of distinct months seen

    Returns:
        dict: stats payload ready to be returned by GET /api/orders/stats
    """
    connection = get_connection()
    cursor = connection.cursor()

    # --- Total order count ---
    cursor.execute("SELECT COUNT(*) AS cnt FROM orders")
    total_orders = cursor.fetchone()["cnt"]

    # --- Count per status ---
    cursor.execute(
        "SELECT status, COUNT(*) AS cnt FROM orders GROUP BY status"
    )
    status_rows = cursor.fetchall()

    # Build a dict with all known statuses defaulting to 0
    orders_by_status = {
        "ordered":          0,
        "processing":       0,
        "shipped":          0,
        "out-for-delivery": 0,
        "delivered":        0,
        "cancelled":        0,
    }
    for row in status_rows:
        if row["status"] in orders_by_status:
            orders_by_status[row["status"]] = row["cnt"]

    # --- Estimate total spent ---
    # We parse every price string, strip currency symbols, and sum the
    # numbers we can parse. Unparseable strings are quietly skipped.
    cursor.execute("SELECT price FROM orders WHERE price IS NOT NULL AND price != ''")
    price_rows = cursor.fetchall()

    total_spent = 0.0
    parsed_price_count = 0

    for price_row in price_rows:
        raw = price_row["price"]
        try:
            # Strip common currency symbols and whitespace, then convert
            cleaned = raw.replace("$", "").replace("£", "").replace("€", "").replace(",", "").strip()
            value = float(cleaned)
            total_spent += value
            parsed_price_count += 1
        except (ValueError, AttributeError):
            # Price string couldn't be parsed — skip it silently
            pass

    # Format with 2 decimal places and a $ prefix for display
    total_spent_str = f"${total_spent:.2f}" if total_spent > 0 else "N/A"

    # --- Monthly average ---
    # Count distinct year-month combinations from created_at timestamps
    cursor.execute(
        "SELECT DISTINCT strftime('%Y-%m', created_at) AS month FROM orders"
    )
    month_rows = cursor.fetchall()
    num_months = max(len(month_rows), 1)  # Avoid division by zero

    monthly_average = total_spent / num_months if total_spent > 0 else 0.0
    monthly_average_str = f"${monthly_average:.2f}" if total_spent > 0 else "N/A"

    connection.close()

    return {
        "total_orders":        total_orders,
        "total_spent_estimate": total_spent_str,
        "orders_by_status":    orders_by_status,
        "monthly_average":     monthly_average_str,
    }


# ---------------------------------------------------------------------------
# Analytics helpers — power the /api/analytics/overview and /security routes
# ---------------------------------------------------------------------------


def get_analytics_overview():
    """
    Computes full analytics stats from the processed_emails table.

    How each field is calculated:
        total_today       — COUNT(*) WHERE date(processed_at) = today's date
        spam_count        — COUNT(*) WHERE is_spam = 1
        flagged_suspicious— COUNT(*) WHERE category = 'spam' AND is_spam = 0
                            (classified as spam-like by AI even if not flagged)
        by_category       — GROUP BY category → dict of {category: count}
        by_sender_domain  — extract domain from sender (text after '@'), GROUP BY
                            domain, take top 5, remainder bucketed as 'other'
        hourly_volume     — GROUP BY hour(processed_at) for today's emails,
                            returns list of {hour: '8am', count: N} for hours
                            00–23 that have at least one email

    Returns:
        dict: overview stats payload
    """
    connection = get_connection()
    cursor = connection.cursor()

    # --- Total emails processed today ---
    # date() extracts YYYY-MM-DD from the TIMESTAMP so we can compare to today
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM processed_emails WHERE date(processed_at) = date('now')"
    )
    total_today = cursor.fetchone()["cnt"]

    # --- Spam count ---
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM processed_emails WHERE is_spam = 1"
    )
    spam_count = cursor.fetchone()["cnt"]

    # --- Flagged suspicious ---
    # Emails classified as 'spam' by the AI but NOT marked is_spam in DB
    # are treated as "suspicious" — they could be phishing, spoofed senders, etc.
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM processed_emails WHERE category = 'spam' AND is_spam = 0"
    )
    flagged_suspicious = cursor.fetchone()["cnt"]

    # --- By category ---
    # Group all processed emails by their AI-assigned category.
    cursor.execute(
        "SELECT category, COUNT(*) AS cnt FROM processed_emails GROUP BY category ORDER BY cnt DESC"
    )
    by_category = {}
    for row in cursor.fetchall():
        # Guard against NULL categories (shouldn't happen but be safe)
        cat = row["category"] or "unknown"
        by_category[cat] = row["cnt"]

    # --- By sender domain ---
    # The sender column holds the raw email address (e.g. "alice@gmail.com").
    # We extract everything after '@' using SQLite's substr + instr functions.
    # Top 5 domains are returned individually; the rest are summed as "other".
    cursor.execute(
        """SELECT
               CASE
                   WHEN instr(sender, '@') > 0
                   THEN lower(substr(sender, instr(sender, '@') + 1))
                   ELSE 'unknown'
               END AS domain,
               COUNT(*) AS cnt
           FROM processed_emails
           GROUP BY domain
           ORDER BY cnt DESC"""
    )
    domain_rows = cursor.fetchall()

    by_sender_domain = {}
    other_count = 0
    for index, row in enumerate(domain_rows):
        if index < 5:
            # Keep the top 5 domains as individual keys
            by_sender_domain[row["domain"]] = row["cnt"]
        else:
            # Bucket everything beyond the top 5 into "other"
            other_count += row["cnt"]

    if other_count > 0:
        by_sender_domain["other"] = other_count

    # --- Hourly volume (today only) ---
    # strftime('%H', processed_at) returns a zero-padded 24h hour string like '08'.
    # We convert it to a human-friendly label like '8am' / '3pm'.
    cursor.execute(
        """SELECT
               CAST(strftime('%H', processed_at) AS INTEGER) AS hour_num,
               COUNT(*) AS cnt
           FROM processed_emails
           WHERE date(processed_at) = date('now')
           GROUP BY hour_num
           ORDER BY hour_num ASC"""
    )
    hourly_rows = cursor.fetchall()

    hourly_volume = []
    for row in hourly_rows:
        hour_num = row["hour_num"]
        # Convert 24h integer to 12h label (0→12am, 13→1pm, etc.)
        if hour_num == 0:
            label = "12am"
        elif hour_num < 12:
            label = f"{hour_num}am"
        elif hour_num == 12:
            label = "12pm"
        else:
            label = f"{hour_num - 12}pm"

        hourly_volume.append({"hour": label, "count": row["cnt"]})

    connection.close()

    return {
        "total_today":        total_today,
        "spam_count":         spam_count,
        "flagged_suspicious": flagged_suspicious,
        "by_category":        by_category,
        "by_sender_domain":   by_sender_domain,
        "hourly_volume":      hourly_volume,
    }


def get_analytics_security():
    """
    Computes security-focused statistics from the processed_emails table.

    How each field is calculated:
        spam_rate_percent    — (spam_count / total) * 100, rounded to 1 dp
        safe_percent         — 100 - spam_rate_percent
        suspicious_senders   — senders whose domain appears ≤1 time in the
                               table AND whose email was classified as spam;
                               reason is a human-readable explanation

    Returns:
        dict: {spam_rate_percent, suspicious_senders, safe_percent}
    """
    connection = get_connection()
    cursor = connection.cursor()

    # --- Total processed + spam count ---
    cursor.execute("SELECT COUNT(*) AS cnt FROM processed_emails")
    total = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM processed_emails WHERE is_spam = 1")
    spam_count = cursor.fetchone()["cnt"]

    # Compute percentages, guarding against division by zero
    if total > 0:
        spam_rate = round((spam_count / total) * 100, 1)
    else:
        spam_rate = 0.0

    safe_percent = round(100.0 - spam_rate, 1)

    # --- Suspicious senders ---
    # A sender is considered suspicious if:
    #   1. Their email was classified as spam OR is marked is_spam = 1
    #   2. Their domain appears only once (one-off / throwaway address pattern)
    #
    # We retrieve them from the DB and generate a plain-English reason string
    # in Python so the reason is readable rather than a raw SQL label.
    cursor.execute(
        """SELECT sender, category, is_spam,
               CASE
                   WHEN instr(sender, '@') > 0
                   THEN lower(substr(sender, instr(sender, '@') + 1))
                   ELSE 'unknown'
               END AS domain
           FROM processed_emails
           WHERE is_spam = 1 OR category = 'spam'
           ORDER BY processed_at DESC
           LIMIT 20"""
    )
    spam_rows = cursor.fetchall()

    # Count how many times each domain appears in the full table
    cursor.execute(
        """SELECT
               CASE
                   WHEN instr(sender, '@') > 0
                   THEN lower(substr(sender, instr(sender, '@') + 1))
                   ELSE 'unknown'
               END AS domain,
               COUNT(*) AS cnt
           FROM processed_emails
           GROUP BY domain"""
    )
    domain_counts = {row["domain"]: row["cnt"] for row in cursor.fetchall()}

    connection.close()

    suspicious_senders = []
    seen_senders = set()  # Avoid duplicate entries for the same address

    for row in spam_rows:
        sender = row["sender"] or "unknown"

        # Skip duplicates — one entry per unique sender is enough
        if sender in seen_senders:
            continue
        seen_senders.add(sender)

        domain = row["domain"]
        domain_freq = domain_counts.get(domain, 0)

        # Build a human-readable reason string based on what we know
        reasons = []
        if row["is_spam"] == 1:
            reasons.append("flagged as spam by AI classifier")
        elif row["category"] == "spam":
            reasons.append("categorised as spam (not explicitly flagged)")
        if domain_freq == 1:
            reasons.append("sender domain seen only once (possible throwaway)")

        reason = "; ".join(reasons) if reasons else "suspicious activity detected"

        suspicious_senders.append({"email": sender, "reason": reason})

    return {
        "spam_rate_percent":  spam_rate,
        "suspicious_senders": suspicious_senders,
        "safe_percent":       safe_percent,
    }
