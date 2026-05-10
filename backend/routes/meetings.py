
from db.sqlite import get_meetings as db_get_meetings
from db.sqlite import save_meeting
from fastapi import APIRouter
from pipeline.meeting_extractor import extract_meetings as run_meeting_extractor
from pydantic import BaseModel

router = APIRouter()


class MeetingExtractRequest(BaseModel):

    subject: str
    body: str
    sender: str


@router.get("")
def get_meetings():
    try:
        return db_get_meetings()
    except Exception as exc:
        print(f"[MeetingsRoute] Failed to fetch meetings: {exc}")
        return []


@router.post("/extract")
def extract_meetings(req: MeetingExtractRequest):
    try:
        extracted = run_meeting_extractor(req.subject, req.body, req.sender)
        meetings = extracted.get("meetings", [])

        saved = []
        for meeting in meetings:
            meeting_id = save_meeting(
                title=meeting.get("title", "").strip(),
                date=meeting.get("date"),
                time=meeting.get("time"),
                location_or_link=meeting.get("location_or_link"),
                attendees=meeting.get("attendees", []),
                source_email_subject=meeting.get(
                    "source_email_subject", req.subject
                ),
            )
            saved.append({"id": meeting_id, **meeting})

        return {"success": True, "count": len(saved), "meetings": saved}
    except Exception as exc:
        print(f"[MeetingsRoute] Extraction failed: {exc}")
        return {
            "success": False,
            "count": 0,
            "meetings": [],
            "error": str(exc),
        }
