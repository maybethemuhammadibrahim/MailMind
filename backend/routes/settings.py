
from db.sqlite import delete_all_data, get_all_settings, set_setting
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


DEFAULTS = {
    "tone": "professional",
    "auto_draft": "true",
    "vocabulary": "Concise,Action-oriented",
}


class AISettingsRequest(BaseModel):

    tone: str | None = None
    auto_draft: str | None = None
    vocabulary: str | None = None


@router.get("")
def read_settings():
    try:
        settings = get_all_settings()

        if not settings:
            print("[Settings] No settings found — seeding defaults.")
            for key, value in DEFAULTS.items():
                set_setting(key, value)
            settings = DEFAULTS.copy()

        return settings

    except Exception as exc:
        print(f"[Settings] Failed to read settings: {exc}")
        return {"error": f"Failed to read settings: {str(exc)}"}


@router.patch("/ai")
def update_ai_settings(req: AISettingsRequest):
    try:
        updated_keys = []

        if req.tone is not None:
            set_setting("tone", req.tone)
            updated_keys.append("tone")

        if req.auto_draft is not None:
            set_setting("auto_draft", req.auto_draft)
            updated_keys.append("auto_draft")

        if req.vocabulary is not None:
            set_setting("vocabulary", req.vocabulary)
            updated_keys.append("vocabulary")

        print(f"[Settings] Updated: {updated_keys}")
        return {"success": True, "updated": updated_keys}

    except Exception as exc:
        print(f"[Settings] Failed to update AI settings: {exc}")
        return {"error": f"Failed to update settings: {str(exc)}"}


@router.delete("/data")
def wipe_all_data():
    try:
        delete_all_data()
        return {
            "success": True,
            "message": "All processed data has been deleted. Your settings were preserved.",
        }

    except Exception as exc:
        print(f"[Settings] Failed to delete data: {exc}")
        return {"error": f"Failed to delete data: {str(exc)}"}
