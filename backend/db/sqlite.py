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
            classification  TEXT,
            summary         TEXT,
            draft_reply     TEXT,
            draft_confidence REAL,
            draft_subject   TEXT,
            fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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

    # IGNORE means: if this email_id already exists, skip silently.
    # This preserves any cached AI results on the existing row.
    cursor.execute(
        """INSERT OR IGNORE INTO emails
           (email_id, subject, sender, sender_email, body_plain, thread_id, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            email_id,
            email_dict.get("subject", ""),
            email_dict.get("sender", ""),
            email_dict.get("sender_email", ""),
            email_dict.get("body_plain", ""),
            email_dict.get("thread_id", ""),
            email_dict.get("timestamp", ""),
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
