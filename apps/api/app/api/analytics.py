from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsService
from app.api.schemas import PullRequestDetailOut, PullRequestOut, pr_to_detail, pr_to_out
from app.db.session import get_session

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def summary(
    repository: str | None = None,
    author: str | None = None,
    days: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await AnalyticsService(session).summary(repository, author, days)


@router.get("/trends")
async def trends(
    days: int = 30,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await AnalyticsService(session).trends(days)


@router.get("/findings")
async def findings(
    days: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await AnalyticsService(session).findings(days)


@router.get("/repositories")
async def repositories(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await AnalyticsService(session).repositories()


@router.get("/authors")
async def authors(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await AnalyticsService(session).authors()


@router.get("/authors/{author}")
async def author_detail(author: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    item = await AnalyticsService(session).author_detail(author)
    if item is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return item


@router.get("/prs", response_model=list[PullRequestOut])
async def analytics_prs(
    repository: str | None = None,
    risk: str | None = None,
    status: str | None = None,
    author: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[PullRequestOut]:
    items = await AnalyticsService(session).list_prs(repository, risk, status, author)
    return [pr_to_out(item) for item in items]


@router.get("/prs/{repository:path}/{number}", response_model=PullRequestDetailOut)
async def analytics_pr_detail(
    repository: str,
    number: int,
    session: AsyncSession = Depends(get_session),
) -> PullRequestDetailOut:
    item = await AnalyticsService(session).get_pr(repository, number)
    if item is None:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr_to_detail(item)
