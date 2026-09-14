from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import SettingsOut
from app.config import Settings, get_settings
from app.db.session import get_session
from app.policy.engine import NEVER_ALLOWED, PolicyEngine
from app.rules.loader import load_review_rules
from app.runtime import get_runtime_controls
from app.scm.base import provider_label

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
async def get_app_settings(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> SettingsOut:
    loaded = load_review_rules(settings.config_dir)
    policy = PolicyEngine(loaded.global_rules.automation)
    controls = await get_runtime_controls(session, settings)
    return SettingsOut(
        automation_mode=loaded.global_rules.automation.mode,
        allowed_actions=list(policy.allowed),
        forbidden_actions=sorted({*policy.forbidden, *(item.value for item in NEVER_ALLOWED)}),
        ai_enabled=controls.ai_enabled,
        pr_comments_enabled=controls.pr_comments_enabled,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model,
        scm_provider=settings.git_provider,
        scm_configured=settings.scm_configured,
        gitea_configured=settings.scm_configured,
        merge_authority="human",
        notes=[
            "AI recommendations are advisory only.",
            "The system never merges or approves pull requests.",
            f"Merge actions remain in {provider_label(settings.git_provider)} under human control.",
        ],
    )
