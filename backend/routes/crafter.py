
from fastapi import APIRouter
from pipeline.crafter import craft_email, get_quick_prompts
from pydantic import BaseModel

router = APIRouter()


class CraftRequest(BaseModel):

    prompt: str
    tone: str = "professional"
    recipient: str = ""
    subject: str = ""


class CraftSendRequest(BaseModel):

    to: str
    subject: str
    body: str


@router.post("/generate")
def generate_email(req: CraftRequest):
    if not req.prompt.strip():
        return {"error": "Prompt cannot be empty. Describe what you want to say."}

    try:
        result = craft_email(
            prompt=req.prompt.strip(),
            tone=req.tone.strip(),
            recipient=req.recipient.strip(),
            subject=req.subject.strip(),
        )
        return result

    except Exception as exc:
        print(f"[Crafter API] generate failed: {exc}")
        return {"error": f"Failed to generate email: {str(exc)}"}


@router.get("/quick-prompts")
def list_quick_prompts():
    return get_quick_prompts()
