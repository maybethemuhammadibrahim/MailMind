
from pipeline.gemini import call_fast


def extract_todos(subject, body, sender):
    prompt = f"""
Email Subject: {subject}
Sender: {sender}
Email Body:
{body[:2000]}
""".strip()

    system = """
You are an extraction assistant for productivity tasks.
Extract actionable to-do items from the email.
Return ONLY valid JSON with this exact shape:
{
  "todos": [
    {
      "title": "string (max 10 words)",
      "due_date": "string or null",
      "priority": "high|medium|low",
      "source_email_subject": "string"
    }
  ]
}
If there are no todos, return {"todos": []}.
""".strip()

    try:
        raw = call_fast(prompt=prompt, system=system)
        todos = raw.get("todos", []) if isinstance(raw, dict) else []

        cleaned_todos = []
        for item in todos:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            if not title:
                continue

            due_date = item.get("due_date")
            due_date = str(due_date).strip() if due_date not in (None, "") else None

            priority = str(item.get("priority", "medium")).strip().lower()
            if priority not in ("high", "medium", "low"):
                priority = "medium"

            cleaned_todos.append(
                {
                    "title": title,
                    "due_date": due_date,
                    "priority": priority,
                    "source_email_subject": str(
                        item.get("source_email_subject") or subject
                    ).strip(),
                }
            )

        return {"todos": cleaned_todos}
    except Exception as exc:
        print(f"[TodoExtractor] Gemini extraction failed: {exc}")
        return {"todos": []}
