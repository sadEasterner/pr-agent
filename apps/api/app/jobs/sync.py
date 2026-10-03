from __future__ import annotations

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models import PullRequest
from app.gitea.client import GiteaClient
from app.gitea.models import GiteaPullRequest
from app.jobs.queue import JobQueue
from app.logging import get_logger
from app.scm.events import PullRequestEvent, WebhookBranch, WebhookPullRequest, WebhookRepository, WebhookUser

logger = get_logger(__name__)


class PullRequestSync:
    """Polls Gitea for open PRs when inbound webhooks time out."""

    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        queue: JobQueue,
        client: GiteaClient,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._queue = queue
        self._client = client
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        interval = max(15.0, self._settings.scm_sync_interval_seconds)
        while True:
            try:
                await self.tick()
            except Exception:
                logger.exception("pr_sync_failed")
            await asyncio.sleep(interval)

    async def tick(self) -> None:
        repositories = await self._repositories()
        for repository in repositories:
            pulls = await self._client.list_open_pulls(repository)
            for pull in pulls:
                event = await self._event_if_needed(repository, pull)
                if event is None:
                    continue
                await self._queue.enqueue(event)
                logger.info(
                    "pr_sync_enqueued",
                    repository=repository,
                    pr_number=pull.number,
                    action=event.action,
                    head_sha=event.head_sha,
                )

    async def _repositories(self) -> list[str]:
        repos = set(self._settings.scm_sync_repository_list)
        repos.update(_repos_from_config(self._settings.repository_rules_dir))
        async with self._session_factory() as session:
            result = await session.execute(select(PullRequest.repository).distinct())
            repos.update(row[0] for row in result.all() if row[0])
        return sorted(repos)

    async def _event_if_needed(
        self,
        repository: str,
        pull: GiteaPullRequest,
    ) -> PullRequestEvent | None:
        sha = pull.head.sha if pull.head else ""
        if not sha or pull.number <= 0:
            return None
        async with self._session_factory() as session:
            result = await session.execute(
                select(PullRequest).where(
                    PullRequest.repository == repository,
                    PullRequest.number == pull.number,
                )
            )
            existing = result.scalar_one_or_none()
        if existing and existing.latest_sha == sha:
            return None
        action = "synchronized" if existing else "opened"
        return pull_to_event(repository, pull, action)


def pull_to_event(repository: str, pull: GiteaPullRequest, action: str) -> PullRequestEvent:
    login = pull.user.login if pull.user else "unknown"
    head = pull.head
    base = pull.base
    return PullRequestEvent(
        action=action,
        number=pull.number,
        provider="gitea",
        pull_request=WebhookPullRequest(
            number=pull.number,
            title=pull.title,
            body=pull.body or "",
            html_url=pull.html_url,
            state=pull.state,
            merged=pull.merged,
            created_at=pull.created_at.isoformat() if pull.created_at else None,
            closed_at=pull.closed_at.isoformat() if pull.closed_at else None,
            merged_at=pull.merged_at.isoformat() if pull.merged_at else None,
            user=WebhookUser(login=login),
            head=WebhookBranch(ref=head.ref if head else "", sha=head.sha if head else ""),
            base=WebhookBranch(ref=base.ref if base else "", sha=base.sha if base else ""),
        ),
        repository=WebhookRepository(
            full_name=repository,
            name=repository.rsplit("/", 1)[-1],
        ),
        sender=WebhookUser(login=login),
    )


def _repos_from_config(rules_dir) -> set[str]:
    repos: set[str] = set()
    if not rules_dir.exists():
        return repos
    for path in rules_dir.glob("*.yaml"):
        if path.stem.startswith("example") or path.stem == "README":
            continue
        if "__" not in path.stem:
            continue
        owner, repo = path.stem.split("__", 1)
        repos.add(f"{owner}/{repo}")
    return repos


def gitea_client_from_scm(scm: object) -> GiteaClient | None:
    client = getattr(scm, "client", None)
    return client if isinstance(client, GiteaClient) else None
