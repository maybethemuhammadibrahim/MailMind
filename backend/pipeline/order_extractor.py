

from pipeline.gemini import call_fast


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

VALID_STATUSES = {
    "ordered",
    "processing",
    "shipped",
    "out-for-delivery",
    "delivered",
    "cancelled",
}


def _build_prompt(subject, body, sender):
    body_preview = body[:3000] if body else ""

    prompt = (
        f"From: {sender}\n"
        f"Subject: {subject}\n\n"
        f"Body:\n{body_preview}\n\n"
        "Extract the order/purchase information from the email above."
    )
    return prompt


def _sanitize_result(result):
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

    if clean["status"] not in VALID_STATUSES:
        print(f"[OrderExtractor] Unexpected status '{clean['status']}' — defaulting to 'processing'")
        clean["status"] = "processing"

    return clean


def extract_order(subject, body, sender):
    print(f"[OrderExtractor] Extracting order — subject='{subject[:60]}'")

    prompt = _build_prompt(subject, body, sender)

    try:
        result = call_fast(prompt, ORDER_SYSTEM_PROMPT)
        clean = _sanitize_result(result)
        print(f"[OrderExtractor] Success — retailer={clean['retailer']}, status={clean['status']}")
        return clean
    except Exception as exc:
        print(f"[OrderExtractor] Extraction failed: {exc}. Returning safe default.")
        return DEFAULT_ORDER
