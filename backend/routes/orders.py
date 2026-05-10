
from db.sqlite import get_orders as db_get_orders
from db.sqlite import get_order_stats, save_order
from fastapi import APIRouter, HTTPException
from pipeline.order_extractor import extract_order
from pydantic import BaseModel

router = APIRouter()


class OrderItem(BaseModel):

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

    total_orders: int
    total_spent_estimate: str
    orders_by_status: dict
    monthly_average: str


class ExtractOrderRequest(BaseModel):

    email_id: str
    subject: str
    body: str
    sender: str


@router.get("", response_model=list[OrderItem])
def list_orders():
    print("[Route GET /orders] Fetching all orders")

    orders = db_get_orders()

    print(f"[Route GET /orders] Returning {len(orders)} orders")
    return orders


@router.get("/stats", response_model=OrderStatsResponse)
def order_stats():
    print("[Route GET /orders/stats] Computing order statistics")

    stats = get_order_stats()

    print(f"[Route GET /orders/stats] total_orders={stats['total_orders']}")
    return stats


@router.post("/extract")
def extract_and_save_order(req: ExtractOrderRequest):
    print(
        f"[Route POST /orders/extract] email_id={req.email_id}, "
        f"subject='{req.subject[:60]}'"
    )

    order_data = extract_order(req.subject, req.body, req.sender)

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

    return {"id": order_id, **order_data}
