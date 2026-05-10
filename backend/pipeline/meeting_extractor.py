
from pipeline.gemini import call_fast


def extract_meetings(subject, body, sender):
    prompt = f"""
Email Subject: {subject}
Sender: {sender}
Email Body:
{body[:2000]}
""".strip()

    system = """
You are an extraction assistant for meeting events.
Extract any meeting, call, or calendar event mentioned in the email.
Return ONLY valid JSON with this exact shape:
{
  "meetings": [
    {
      "title": "string",
      "date": "string or null",
      "time": "string or null",
      "location_or_link": "string or null",
      "attendees": ["string"],
      "source_email_subject": "string"
    }
  ]
}
If there are no meetings, return {"meetings": []}.
""".strip()

    try:
        raw = call_fast(prompt=prompt, system=system)
        meetings = raw.get("meetings", []) if isinstance(raw, dict) else []

        cleaned_meetings = []
        for item in meetings:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            if not title:
                continue

            date = item.get("date")
            date = str(date).strip() if date not in (None, "") else None

            time = item.get("time")
            time = str(time).strip() if time not in (None, "") else None

            location = item.get("location_or_link")
            location = (
                str(location).strip() if location not in (None, "") else None
            )

            attendees = item.get("attendees", [])
            if not isinstance(attendees, list):
                attendees = []
            attendees = [str(a).strip() for a in attendees if str(a).strip()]

            cleaned_meetings.append(
                {
                    "title": title,
                    "date": date,
                    "time": time,
                    "location_or_link": location,
                    "attendees": attendees,
                    "source_email_subject": str(
                        item.get("source_email_subject") or subject
                    ).strip(),
                }
            )

        return {"meetings": cleaned_meetings}
    except Exception as exc:
        print(f"[MeetingExtractor] Gemini extraction failed: {exc}")
        return {"meetings": []}
