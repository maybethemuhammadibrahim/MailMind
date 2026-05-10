
from db.sqlite import get_todos as db_get_todos
from db.sqlite import mark_todo_done as db_mark_todo_done
from db.sqlite import save_todo
from fastapi import APIRouter
from pipeline.todo_extractor import extract_todos as run_todo_extractor
from pydantic import BaseModel

router = APIRouter()


class TodoExtractRequest(BaseModel):

    subject: str
    body: str
    sender: str


@router.get("")
def get_todos(include_done: bool = False):
    try:
        return db_get_todos(include_done=include_done)
    except Exception as exc:
        print(f"[TodosRoute] Failed to fetch todos: {exc}")
        return []


@router.patch("/{todo_id}/done")
def mark_todo_done(todo_id: int):
    try:
        updated = db_mark_todo_done(todo_id)
        if not updated:
            return {"success": False, "message": "Todo not found."}
        return {"success": True, "todo_id": todo_id}
    except Exception as exc:
        print(f"[TodosRoute] Failed to mark todo done ({todo_id}): {exc}")
        return {"success": False, "message": str(exc)}


@router.post("/extract")
def extract_todos(req: TodoExtractRequest):
    try:
        extracted = run_todo_extractor(req.subject, req.body, req.sender)
        todos = extracted.get("todos", [])

        saved = []
        for todo in todos:
            todo_id = save_todo(
                title=todo.get("title", "").strip(),
                due_date=todo.get("due_date"),
                priority=todo.get("priority", "medium"),
                source_email_subject=todo.get("source_email_subject", req.subject),
            )
            saved.append({"id": todo_id, **todo})

        return {"success": True, "count": len(saved), "todos": saved}
    except Exception as exc:
        print(f"[TodosRoute] Extraction failed: {exc}")
        return {"success": False, "count": 0, "todos": [], "error": str(exc)}
