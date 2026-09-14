from fastapi import APIRouter, Depends

from app.api.schemas import SettingsOut
from app.config import Settings, get_settings
from app.policy.engine import NEVER_ALLOWED, PolicyEngine
from app.rules.loader import load_review_rules

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
async def get_app_settings(settings: Settings = Depends(get_settings)) -> SettingsOut:
    loaded = load_review_rules(settings.config_dir)
    policy = PolicyEngine(loaded.global_rules.automation)
    return SettingsOut(
        automation_mode=loaded.global_rules.automation.mode,
        allowed_actions=list(policy.allowed),
        forbidden_actions=sorted({*policy.forbidden, *(item.value for item in NEVER_ALLOWED)}),
        ai_enabled=settings.ai_enabled,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model,
        gitea_configured=bool(settings.gitea_token and settings.gitea_base_url),
        merge_authority="human",
        notes=[
            "AI recommendations are advisory only.",
            "The system never merges or approves pull requests.",
            "Merge actions remain in Gitea under human control.",
        ],
    )
