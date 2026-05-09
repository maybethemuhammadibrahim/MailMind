# backend/routes/pipeline.py
# ---------------------------------------------------------------
# FastAPI router exposing the AI pipeline (classify, summarize,
# draft) as REST endpoints, plus a single /process-email route
# that runs all three stages in sequence.
# ---------------------------------------------------------------

# ---------------------------------------------------------------------------
# Why Pydantic?
# Pydantic validates every incoming JSON request body automatically.
# If a required field is missing or has the wrong type, FastAPI returns
# a 422 Unprocessable Entity before our code ever runs -- keeping invalid
# data out of the business logic entirely and making error messages clear.
# ---------------------------------------------------------------------------

from db.sqlite import (
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
from pipeline.summarizer import summarize_email
from pipeline.todo_extractor import extract_todos
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request models -- one per endpoint
# ---------------------------------------------------------------------------


class ClassifyRequest(BaseModel):
    """Fields required to classify a single email."""

    email_id: str
    subject: str
    sender: str
    body: str


class SummarizeRequest(BaseModel):
    """Fields required to summarise a single email."""

    subject: str
    body: str


class DraftRequest(BaseModel):
    """Fields required to draft a reply; classification and summary are pre-computed."""

    subject: str
    body: str
    classification: dict
    summary: dict
    email_id: str | None = None


class ProcessEmailRequest(BaseModel):
    """All fields delivered by the n8n Gmail webhook for a full pipeline run."""

    email_id: str
    subject: str
    sender: str
    sender_email: str
    body_plain: str
    thread_id: str = ""
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/classify")
def classify(req: ClassifyRequest):
    """
    Classifies a single email and records it as processed.

    Calls Gemini Flash with few-shot examples to assign a category,
    priority score, and spam/order flags, then persists the result
    so the same email won't be re-processed on the next Gmail poll.

    Args:
        req (ClassifyRequest): validated request -- email_id, subject, sender, body

    Returns:
        dict: email_id merged with all classification fields
    """
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
    """
    Summarises an email into a headline, key facts, and action items.

    Purely read-only -- does not write to the database. Safe to call
    independently of /classify, for example when the UI requests a
    fresh summary for an already-processed email.

    Args:
        req (SummarizeRequest): validated request -- subject and body

    Returns:
        dict: one_line_summary, key_facts, action_items
    """
    print(f"[Route /summarize] subject='{req.subject[:60]}'")
    return summarize_email(req.subject, req.body)


@router.post("/draft")
def draft(req: DraftRequest):
    """
    Generates a professional email reply draft.

    Expects pre-computed classification and summary dicts so the model
    has full context (urgency, tone, required actions) before composing.

    Args:
        req (DraftRequest): validated request -- subject, body,
                            classification dict, summary dict

    Returns:
        dict: draft_reply, confidence_score, suggested_subject
    """
    print(f"[Route /draft] subject='{req.subject[:60]}'")
    result = draft_reply(req.subject, req.body, req.classification, req.summary)

    # If email_id is provided, persist regenerate results for cache reuse.
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
    """
    Runs classify, summarize, draft, todo extraction, and meeting
    extraction in sequence for one email.

    Skips mark_processed if the email_id already exists in the database.
    The pipeline always executes so callers receive fresh AI results.

    Args:
        req (ProcessEmailRequest): validated request with all email fields

    Returns:
          dict: email_id, classification, summary, draft, extracted entities,
              already_processed
    """
    print(
        f"[Route /process-email] email_id={req.email_id}, subject='{req.subject[:60]}'"
    )
    already = is_processed(req.email_id)
    classification = classify_email(req.subject, req.sender_email, req.body_plain)
    summary = summarize_email(req.subject, req.body_plain)
    draft = draft_reply(req.subject, req.body_plain, classification, summary)

    saved_todos = []
    saved_meetings = []
    saved_order = None

    # Avoid duplicate entity inserts when the same email is re-processed.
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

        # Only extract order data if the classifier flagged this as an order email.
        # Avoids wasting Gemini tokens on non-purchase emails.
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

    # Ensure the source email row exists, then persist all AI outputs.
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
