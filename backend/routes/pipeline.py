

from db.sqlite import (
    get_email,
    is_processed,
    mark_processed,
    save_meeting,
    save_draft,
    save_email,
    save_order,
    save_pipeline_result,
    save_todo,
)
from fastapi import APIRouter
from pipeline.classifier import classify_email
from pipeline.drafter import draft_reply
from pipeline.meeting_extractor import extract_meetings
from pipeline.order_extractor import extract_order
from pipeline.sentiment import analyze_sentiment
from pipeline.summarizer import summarize_email
from pipeline.todo_extractor import extract_todos
from pydantic import BaseModel

router = APIRouter()


class ClassifyRequest(BaseModel):

    email_id: str
    subject: str
    sender: str
    body: str


class SummarizeRequest(BaseModel):

    subject: str
    body: str


class DraftRequest(BaseModel):

    subject: str
    body: str
    classification: dict
    summary: dict
    email_id: str | None = None
    thread_id: str = ""


class SentimentRequest(BaseModel):

    subject: str
    body: str
    sender: str


class ProcessEmailRequest(BaseModel):

    email_id: str
    subject: str
    sender: str
    sender_email: str
    body_plain: str
    thread_id: str = ""
    timestamp: str = ""


@router.post("/sentiment")
def sentiment(req: SentimentRequest):
    print(f"[Route /sentiment] subject='{req.subject[:60]}'")
    return analyze_sentiment(req.subject, req.body, req.sender)


@router.post("/classify")
def classify(req: ClassifyRequest):
    print(f"[Route /classify] email_id={req.email_id}")
    result = classify_email(req.subject, req.sender, req.body)
    mark_processed(
        req.email_id,
        req.subject,
        req.sender,
        result.get("category"),
        result.get("priority_score"),
        result.get("is_spam", False),
    )
    return {"email_id": req.email_id, **result}


@router.post("/summarize")
def summarize(req: SummarizeRequest):
    print(f"[Route /summarize] subject='{req.subject[:60]}'")
    return summarize_email(req.subject, req.body)


@router.post("/draft")
def draft(req: DraftRequest):
    print(f"[Route /draft] subject='{req.subject[:60]}'")
    result = draft_reply(
        req.subject,
        req.body,
        req.classification,
        req.summary,
        thread_id=req.thread_id,
        email_id=req.email_id or "",
    )

    if req.email_id:
        save_draft(
            email_id=req.email_id,
            draft_reply=result.get("draft_reply", ""),
            confidence=result.get("confidence_score", 0.5),
            subject=result.get("suggested_subject", ""),
        )

    return result


@router.post("/process-email")
def process_email(req: ProcessEmailRequest):
    print(
        f"[Route /process-email] email_id={req.email_id}, subject='{req.subject[:60]}'"
    )
    already = is_processed(req.email_id)

    if already:
        import json

        cached = get_email(req.email_id)
        # returns cached results if email already processed
        if cached and cached.get("classification"):
            print(f"[Route /process-email] Cache hit — returning stored results")

            classification = None
            summary = None
            draft = None

            try:
                classification = json.loads(cached["classification"]) if cached["classification"] else None
            except (json.JSONDecodeError, TypeError):
                classification = None

            try:
                summary = json.loads(cached["summary"]) if cached["summary"] else None
            except (json.JSONDecodeError, TypeError):
                summary = None

            if cached.get("draft_reply"):
                draft = {
                    "draft_reply": cached["draft_reply"],
                    "confidence_score": cached.get("draft_confidence", 0.5),
                    "suggested_subject": cached.get("draft_subject", f"Re: {req.subject}"),
                }

            if classification and summary and draft:
                return {
                    "email_id": req.email_id,
                    "classification": classification,
                    "summary": summary,
                    "draft": draft,
                    "todos": [],
                    "meetings": [],
                    "order": None,
                    "already_processed": True,
                }

        print(f"[Route /process-email] Cache incomplete — re-processing")


    classification = classify_email(req.subject, req.sender_email, req.body_plain)
    print(
        f"[Route /process-email] Classification: category={classification.get('category')}, "
        f"sentiment={classification.get('sender_sentiment')}, "
        f"critical={classification.get('is_critical')}"
    )

    sentiment_data = {
        "sender_sentiment": classification.get("sender_sentiment", "neutral"),
        "sentiment_intensity": classification.get("sentiment_intensity", 0.3),
        "is_critical": classification.get("is_critical", False),
        "alert_reason": classification.get("alert_reason", ""),
        "recommended_reply_tone": classification.get("recommended_reply_tone", "professional"),
    }

    summary = summarize_email(req.subject, req.body_plain)

    draft = draft_reply(
        req.subject,
        req.body_plain,
        classification,
        summary,
        sentiment=sentiment_data,
        thread_id=req.thread_id,
        email_id=req.email_id,
    )

    saved_todos = []
    saved_meetings = []
    saved_order = None

    if not already:
        todos_result = extract_todos(req.subject, req.body_plain, req.sender_email)
        meetings_result = extract_meetings(
            req.subject, req.body_plain, req.sender_email
        )

        for todo in todos_result.get("todos", []):
            todo_id = save_todo(
                title=todo.get("title", "").strip(),
                due_date=todo.get("due_date"),
                priority=todo.get("priority", "medium"),
                source_email_subject=todo.get("source_email_subject", req.subject),
            )
            saved_todos.append({"id": todo_id, **todo})

        for meeting in meetings_result.get("meetings", []):
            meeting_id = save_meeting(
                title=meeting.get("title", "").strip(),
                date=meeting.get("date"),
                time=meeting.get("time"),
                location_or_link=meeting.get("location_or_link"),
                attendees=meeting.get("attendees", []),
                source_email_subject=meeting.get("source_email_subject", req.subject),
            )
            saved_meetings.append({"id": meeting_id, **meeting})

        if classification.get("is_order_email", False):
            print(f"[Route /process-email] is_order_email=True — running order extractor")
            order_data = extract_order(req.subject, req.body_plain, req.sender_email)
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
            saved_order = {"id": order_id, **order_data}

    save_email(
        {
            "id": req.email_id,
            "subject": req.subject,
            "sender": req.sender,
            "sender_email": req.sender_email,
            "body_plain": req.body_plain,
            "thread_id": req.thread_id,
            "timestamp": req.timestamp,
        }
    )
    save_pipeline_result(req.email_id, classification, summary, draft)

    if not already:
        mark_processed(
            req.email_id,
            req.subject,
            req.sender_email,
            classification.get("category"),
            classification.get("priority_score"),
            classification.get("is_spam", False),
        )

    return {
        "email_id": req.email_id,
        "classification": classification,
        "summary": summary,
        "draft": draft,
        "todos": saved_todos,
        "meetings": saved_meetings,
        "order": saved_order,
        "already_processed": already,
    }
