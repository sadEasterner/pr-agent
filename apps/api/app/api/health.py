from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await session.execute(text("SELECT 1"))
    missing: list[str] = []
    if not settings.database_url:
        missing.append("DATABASE_URL")
    if not settings.git_webhook_secret:
        missing.append("SCM_WEBHOOK_SECRET")
    if settings.git_provider == "gitea" and not settings.git_base_url:
        missing.append("SCM_BASE_URL")
    return {
        "status": "ready" if not missing else "degraded",
        "database": True,
        "missing_configuration": missing,
        "ai_required_for_readiness": False,
    }
