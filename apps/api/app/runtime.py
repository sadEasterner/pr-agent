from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import RuntimeControl


@dataclass
class RuntimeControls:
    ai_enabled: bool
    pr_comments_enabled: bool


async def get_runtime_controls(session: AsyncSession, settings: Settings) -> RuntimeControls:
    row = await session.get(RuntimeControl, 1)
    if row is None:
        row = RuntimeControl(
            id=1,
            ai_enabled=settings.ai_enabled,
            pr_comments_enabled=True,
        )
        session.add(row)
        await session.flush()
    return RuntimeControls(ai_enabled=row.ai_enabled, pr_comments_enabled=row.pr_comments_enabled)


async def update_runtime_controls(
    session: AsyncSession,
    settings: Settings,
    *,
    ai_enabled: bool | None = None,
    pr_comments_enabled: bool | None = None,
) -> RuntimeControls:
    await get_runtime_controls(session, settings)
    row = await session.get(RuntimeControl, 1)
    assert row is not None
    if ai_enabled is not None:
        row.ai_enabled = ai_enabled
    if pr_comments_enabled is not None:
        row.pr_comments_enabled = pr_comments_enabled
    await session.commit()
    await session.refresh(row)
    return RuntimeControls(ai_enabled=row.ai_enabled, pr_comments_enabled=row.pr_comments_enabled)
