# backend/routes/orders.py
# ---------------------------------------------------------------
# FastAPI router for order and purchase tracking.
# Exposes GET /api/orders (full list) and GET /api/orders/stats
# (aggregate spending/status stats), plus POST /api/orders/extract
# which runs the Gemini extraction pipeline and persists the result.
# ---------------------------------------------------------------

from db.sqlite import get_orders as db_get_orders
from db.sqlite import get_order_stats, save_order
from fastapi import APIRouter, HTTPException
from pipeline.order_extractor import extract_order
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response models — document exactly what each endpoint returns
# ---------------------------------------------------------------------------


class OrderItem(BaseModel):
    """
    Represents a single stored order row as returned by GET /api/orders.
    All nullable fields use Python's Optional pattern (default None).
    """

    id: int
    retailer: str
    order_number: str | None = None
    item_description: str | None = None
    order_date: str | None = None
    estimated_delivery: str | None = None
    status: str
    tracking_number: str | None = None
    tracking_url: str | None = None
    price: str | None = None
    source_email_id: str | None = None
    created_at: str | None = None


class OrderStatsResponse(BaseModel):
    """
    Aggregate statistics payload returned by GET /api/orders/stats.

    Fields:
        total_orders:         total number of stored orders
        total_spent_estimate: formatted currency string (e.g. '$149.99')
        orders_by_status:     dict mapping each status to its row count
        monthly_average:      average monthly spend as a formatted string
    """

    total_orders: int
    total_spent_estimate: str
    orders_by_status: dict
    monthly_average: str


class ExtractOrderRequest(BaseModel):
    """
    Request body for POST /api/orders/extract.
    The caller should only send this request when the classifier
    has already confirmed is_order_email = true.
    """

    email_id: str
    subject: str
    body: str
    sender: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[OrderItem])
def list_orders():
    """
    Returns all stored orders, most recent first.

    Reads from the orders table in SQLite and returns the full list.
    No query parameters — the frontend handles filtering client-side.

    Returns:
        list[OrderItem]: all orders ordered by created_at DESC
    """
    print("[Route GET /orders] Fetching all orders")

    orders = db_get_orders()

    print(f"[Route GET /orders] Returning {len(orders)} orders")
    return orders


@router.get("/stats", response_model=OrderStatsResponse)
def order_stats():
    """
    Computes and returns aggregate spending/status statistics.

    Reads the orders table directly — no external calls.
    Price values are parsed heuristically (stripping $, £, €).

    Returns:
        OrderStatsResponse: total_orders, total_spent_estimate,
                            orders_by_status breakdown, monthly_average
    """
    print("[Route GET /orders/stats] Computing order statistics")

    stats = get_order_stats()

    print(f"[Route GET /orders/stats] total_orders={stats['total_orders']}")
    return stats


@router.post("/extract")
def extract_and_save_order(req: ExtractOrderRequest):
    """
    Runs the Gemini order extraction pipeline on the supplied email
    content and persists the result to the orders table.

    Only call this endpoint when the classifier has flagged
    is_order_email = true — otherwise the extraction will return
    a near-empty default dict wasting tokens.

    Args:
        req (ExtractOrderRequest): email_id, subject, body, sender

    Returns:
        dict: the extracted order fields plus the new DB row id
    """
    print(
        f"[Route POST /orders/extract] email_id={req.email_id}, "
        f"subject='{req.subject[:60]}'"
    )

    # Run the Gemini extraction — returns a sanitized dict or the safe default
    order_data = extract_order(req.subject, req.body, req.sender)

    # Persist to SQLite and get the auto-generated row id back
    try:
        order_id = save_order(
            retailer=order_data.get("retailer", "Unknown"),
            order_number=order_data.get("order_number"),
            item_description=order_data.get("item_description"),
            order_date=order_data.get("order_date"),
            estimated_delivery=order_data.get("estimated_delivery"),
            status=order_data.get("status", "processing"),
            tracking_number=order_data.get("tracking_number"),
            tracking_url=order_data.get("tracking_url"),
            price=order_data.get("price"),
            source_email_id=req.email_id,
        )
    except Exception as exc:
        print(f"[Route POST /orders/extract] DB save failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save order to database")

    print(f"[Route POST /orders/extract] Saved order id={order_id}")

    # Return the extracted data alongside the new DB row id
    return {"id": order_id, **order_data}
