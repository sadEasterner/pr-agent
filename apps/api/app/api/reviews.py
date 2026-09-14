from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsService
from app.api.schemas import PullRequestDetailOut, pr_to_detail
from app.db.session import get_session
from app.webhooks.schemas import (
    GiteaWebhookEvent,
    WebhookBranch,
    WebhookPullRequest,
    WebhookRepository,
    WebhookUser,
)

router = APIRouter(prefix="/api", tags=["reviews"])


@router.post("/prs/{repository:path}/{number}/rereview", response_model=PullRequestDetailOut)
async def request_rereview(
    repository: str,
    number: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PullRequestDetailOut:
    service = AnalyticsService(session)
    existing = await service.get_pr(repository, number)
    if existing is None:
        raise HTTPException(status_code=404, detail="Pull request not found")
    processor = request.app.state.processor
    event = GiteaWebhookEvent(
        action="synchronized",
        number=number,
        pull_request=WebhookPullRequest(
            number=number,
            title=existing.title,
            body=existing.description,
            html_url=existing.gitea_url,
            state=existing.status,
            user=WebhookUser(login=existing.author),
            head=WebhookBranch(ref=existing.source_branch, sha=existing.latest_sha),
            base=WebhookBranch(ref=existing.target_branch),
        ),
        repository=WebhookRepository(full_name=repository),
    )
    await processor.process(event, force=True)
    session.expire_all()
    item = await service.get_pr(repository, number)
    if item is None:
        raise HTTPException(status_code=404, detail="Pull request not found after re-review")
    return pr_to_detail(item)
