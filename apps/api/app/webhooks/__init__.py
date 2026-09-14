from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.jobs.queue import JobQueue
from app.logging import get_logger
from app.webhooks.schemas import GiteaWebhookEvent
from app.webhooks.security import require_gitea_signature

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)

SUPPORTED_ACTIONS = {"opened", "reopened", "synchronized", "synchronize", "edited", "closed", "merged"}


@router.post("/webhooks/gitea", status_code=status.HTTP_202_ACCEPTED)
async def gitea_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_gitea_event: str | None = Header(default=None, alias="X-Gitea-Event"),
) -> dict[str, str]:
    body = await require_gitea_signature(request, settings)
    try:
        payload = GiteaWebhookEvent.model_validate_json(body)
    except ValidationError as exc:
        logger.warning("webhook_malformed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Malformed Gitea webhook payload",
        ) from exc

    event_name = (x_gitea_event or "").lower()
    if event_name and event_name not in {"pull_request", "pullrequest", "pull_request_sync"}:
        logger.info("webhook_ignored_event", gitea_event=event_name)
        return {"status": "ignored"}

    if payload.event_type not in SUPPORTED_ACTIONS and payload.action not in SUPPORTED_ACTIONS:
        logger.info("webhook_ignored_action", action=payload.action)
        return {"status": "ignored"}

    if not payload.repository_name or payload.pr_number is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Webhook is missing repository or pull request number",
        )

    queue: JobQueue = request.app.state.job_queue
    await queue.enqueue(payload)
    logger.info(
        "webhook_accepted",
        repository=payload.repository_name,
        pr_number=payload.pr_number,
        event_type=payload.event_type,
        head_sha=payload.head_sha,
    )
    return {"status": "accepted"}
