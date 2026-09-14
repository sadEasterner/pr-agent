from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.jobs.queue import JobQueue
from app.logging import get_logger
from app.scm.base import SUPPORTED_PROVIDERS, normalize_provider
from app.scm.events import PullRequestEvent, parse_webhook_event
from app.webhooks.security import require_webhook_signature

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)

REVIEW_ACTIONS = {
    "opened",
    "reopened",
    "synchronized",
    "synchronize",
    "edited",
    "update",
    "open",
    "reopen",
}

PULL_EVENTS = {
    "pull_request",
    "pullrequest",
    "pull_request_sync",
    "merge request hook",
    "merge_request",
}


@router.post("/webhooks/scm", status_code=status.HTTP_202_ACCEPTED)
async def configured_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    return await ingest_webhook(normalize_provider(settings.scm_provider), request, settings)


@router.post("/webhooks/{provider}", status_code=status.HTTP_202_ACCEPTED)
async def provider_webhook(
    provider: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    x_gitea_event: str | None = Header(default=None, alias="X-Gitea-Event"),
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_gitlab_event: str | None = Header(default=None, alias="X-Gitlab-Event"),
) -> dict[str, str]:
    del x_gitea_event, x_github_event, x_gitlab_event
    return await ingest_webhook(provider, request, settings)


async def ingest_webhook(provider: str, request: Request, settings: Settings) -> dict[str, str]:
    host = normalize_provider(provider)
    if host not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown Git host")
    body = await require_webhook_signature(host, request, settings)
    try:
        payload = parse_webhook_event(host, body)
    except (ValidationError, ValueError, TypeError, KeyError) as exc:
        logger.warning("webhook_malformed", provider=host, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Malformed webhook payload",
        ) from exc

    event_name = _event_name(host, request)
    if event_name and event_name not in PULL_EVENTS:
        logger.info("webhook_ignored_event", provider=host, event=event_name)
        return {"status": "ignored"}

    if payload.event_type not in REVIEW_ACTIONS and payload.action not in REVIEW_ACTIONS:
        logger.info("webhook_ignored_action", provider=host, action=payload.action)
        return {"status": "ignored"}

    if payload.is_closed_or_merged:
        logger.info(
            "webhook_ignored_closed_pr",
            provider=host,
            repository=payload.repository_name,
            pr_number=payload.pr_number,
            action=payload.action,
        )
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
        provider=host,
        repository=payload.repository_name,
        pr_number=payload.pr_number,
        event_type=payload.event_type,
        head_sha=payload.head_sha,
    )
    return {"status": "accepted"}


def _event_name(provider: str, request: Request) -> str:
    if provider == "github":
        return (request.headers.get("x-github-event") or "").lower()
    if provider == "gitlab":
        return (request.headers.get("x-gitlab-event") or "").lower()
    return (request.headers.get("x-gitea-event") or "").lower()
