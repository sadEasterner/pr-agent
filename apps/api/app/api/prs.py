from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsService
from app.api.schemas import PullRequestDetailOut, PullRequestOut, pr_to_detail, pr_to_out
from app.db.session import get_session

router = APIRouter(prefix="/api", tags=["pull-requests"])


@router.get("/prs", response_model=list[PullRequestOut])
async def list_pull_requests(
    repository: str | None = None,
    risk: str | None = None,
    status: str | None = None,
    author: str | None = None,
    severity: str | None = Query(default=None, alias="finding_severity"),
    session: AsyncSession = Depends(get_session),
) -> list[PullRequestOut]:
    service = AnalyticsService(session)
    items = await service.list_prs(repository, risk, status, author, severity)
    return [pr_to_out(item) for item in items]


@router.get("/prs/{repository:path}/{number}", response_model=PullRequestDetailOut)
async def get_pull_request(
    repository: str,
    number: int,
    session: AsyncSession = Depends(get_session),
) -> PullRequestDetailOut:
    service = AnalyticsService(session)
    item = await service.get_pr(repository, number)
    if item is None:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr_to_detail(item)
