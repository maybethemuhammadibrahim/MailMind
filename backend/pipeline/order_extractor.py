# backend/pipeline/order_extractor.py
# ---------------------------------------------------------------
# Extracts structured order and purchase information from shipping
# and order confirmation emails using Gemini Flash. Only called
# when the classifier sets is_order_email = true.
# ---------------------------------------------------------------

import time

from pipeline.gemini import call_fast

# ---------------------------------------------------------------------------
# System prompt — tells Gemini exactly what fields to extract and
# what the valid values are for the status field.
# ---------------------------------------------------------------------------

ORDER_SYSTEM_PROMPT = (
    "You are extracting order and purchase information from an email. "
    "Return ONLY valid JSON with: "
    "retailer (string), "
    "order_number (string or null), "
    "item_description (string, max 15 words), "
    "order_date (string or null), "
    "estimated_delivery (string or null), "
    "status (one of: ordered, processing, shipped, out-for-delivery, delivered, cancelled), "
    "tracking_number (string or null), "
    "tracking_url (string or null), "
    "price (string or null, include currency symbol)."
)

# ---------------------------------------------------------------------------
# Safe default returned when both Gemini attempts fail
# ---------------------------------------------------------------------------

DEFAULT_ORDER = {
    "retailer": "Unknown",
    "order_number": None,
    "item_description": "Order details unavailable",
    "order_date": None,
    "estimated_delivery": None,
    "status": "processing",
    "tracking_number": None,
    "tracking_url": None,
    "price": None,
}

# Valid values the model is allowed to return for the status field
VALID_STATUSES = {
    "ordered",
    "processing",
    "shipped",
    "out-for-delivery",
    "delivered",
    "cancelled",
}


def _build_prompt(subject, body, sender):
    """
    Builds the user-facing prompt with the email content embedded.

    Args:
        subject (str): the email subject line
        body    (str): the plain-text email body (truncated to 3000 chars)
        sender  (str): the sender's email address

    Returns:
        str: the full prompt to send to Gemini
    """
    # Truncate very long emails to keep token usage reasonable
    body_preview = body[:3000] if body else ""

    prompt = (
        f"From: {sender}\n"
        f"Subject: {subject}\n\n"
        f"Body:\n{body_preview}\n\n"
        "Extract the order/purchase information from the email above."
    )
    return prompt


def _sanitize_result(result):
    """
    Ensures every expected key exists and the status is a valid enum value.
    Any missing key falls back to None; an invalid status defaults to 'processing'.

    Args:
        result (dict): raw dict returned by Gemini

    Returns:
        dict: cleaned order dict ready for storage
    """
    # Ensure all expected keys are present, defaulting missing ones to None
    clean = {
        "retailer":           result.get("retailer") or "Unknown",
        "order_number":       result.get("order_number"),
        "item_description":   result.get("item_description") or "No description",
        "order_date":         result.get("order_date"),
        "estimated_delivery": result.get("estimated_delivery"),
        "status":             result.get("status", "processing"),
        "tracking_number":    result.get("tracking_number"),
        "tracking_url":       result.get("tracking_url"),
        "price":              result.get("price"),
    }

    # Reject unexpected status values to keep the DB consistent
    if clean["status"] not in VALID_STATUSES:
        print(f"[OrderExtractor] Unexpected status '{clean['status']}' — defaulting to 'processing'")
        clean["status"] = "processing"

    return clean


def extract_order(subject, body, sender):
    """
    Extracts order and purchase data from an email using Gemini Flash.

    This function should only be called when the classifier has set
    is_order_email = true, avoiding unnecessary API calls.

    Retry behaviour:
        If call_fast() fails on the first attempt (handled internally by
        call_fast), this function catches the exception, waits 2 seconds,
        and tries once more. On a second failure it returns DEFAULT_ORDER.

    Args:
        subject (str): the email subject line
        body    (str): the plain-text email body
        sender  (str): the sender's email address

    Returns:
        dict: order data with keys:
              retailer, order_number, item_description, order_date,
              estimated_delivery, status, tracking_number, tracking_url, price
    """
    print(f"[OrderExtractor] Extracting order — subject='{subject[:60]}'")

    prompt = _build_prompt(subject, body, sender)

    # Attempt 1 — call_fast() already has one internal retry (see gemini.py),
    # so we wrap it in a second try/except for an extra safety net.
    try:
        result = call_fast(prompt, ORDER_SYSTEM_PROMPT)
        clean = _sanitize_result(result)
        print(f"[OrderExtractor] Success — retailer={clean['retailer']}, status={clean['status']}")
        return clean

    except Exception as exc:
        print(f"[OrderExtractor] First attempt failed: {exc}. Waiting 2s and retrying…")
        time.sleep(2)

    # Attempt 2 — final try before giving up
    try:
        result = call_fast(prompt, ORDER_SYSTEM_PROMPT)
        clean = _sanitize_result(result)
        print(f"[OrderExtractor] Retry success — retailer={clean['retailer']}")
        return clean

    except Exception as exc:
        print(f"[OrderExtractor] Both attempts failed: {exc}. Returning safe default.")
        return DEFAULT_ORDER
