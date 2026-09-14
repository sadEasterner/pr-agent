from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_user
from app.config import Settings, get_settings
from app.db.session import get_session
from app.logging import get_logger
from app.runtime import get_runtime_controls, update_runtime_controls

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminControlsOut(BaseModel):
    username: str
    ai_enabled: bool
    pr_comments_enabled: bool
    ai_provider: str
    ai_model: str


class AdminControlsIn(BaseModel):
    ai_enabled: bool | None = None
    pr_comments_enabled: bool | None = None


@router.get("/controls", response_model=AdminControlsOut)
async def get_controls(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    username: str = Depends(require_admin_user),
) -> AdminControlsOut:
    del request
    controls = await get_runtime_controls(session, settings)
    return AdminControlsOut(
        username=username,
        ai_enabled=controls.ai_enabled,
        pr_comments_enabled=controls.pr_comments_enabled,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model,
    )


@router.patch("/controls", response_model=AdminControlsOut)
async def patch_controls(
    payload: AdminControlsIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    username: str = Depends(require_admin_user),
) -> AdminControlsOut:
    del request
    controls = await update_runtime_controls(
        session,
        settings,
        ai_enabled=payload.ai_enabled,
        pr_comments_enabled=payload.pr_comments_enabled,
    )
    logger.info(
        "admin_controls_updated",
        username=username,
        ai_enabled=controls.ai_enabled,
        pr_comments_enabled=controls.pr_comments_enabled,
    )
    return AdminControlsOut(
        username=username,
        ai_enabled=controls.ai_enabled,
        pr_comments_enabled=controls.pr_comments_enabled,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model,
    )
