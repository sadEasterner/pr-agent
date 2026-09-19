from __future__ import annotations

from app.gitea.client import GiteaClient
from app.logging import get_logger
from app.scm.comments import REVIEW_MARKER, upsert_review_comment
from app.scm.models import PullRequestSnapshot

logger = get_logger(__name__)

__all__ = ["GiteaService", "PullRequestSnapshot", "REVIEW_MARKER"]


class GiteaService:
    name = "gitea"

    def __init__(self, client: GiteaClient) -> None:
        self.client = client

    async def close(self) -> None:
        await self.client.close()

    async def fetch_snapshot(self, repository: str, number: int) -> PullRequestSnapshot:
        pull_request = await self.client.get_pull_request(repository, number)
        files = await self.client.get_changed_files(repository, number)
        try:
            diff = await self.client.get_diff(repository, number)
        except Exception:
            logger.warning("gitea_diff_unavailable", repository=repository, pr_number=number)
            diff = "\n".join(file.patch or "" for file in files)
        commits = await self.client.get_commits(repository, number)
        head_sha = pull_request.head.sha if pull_request.head else ""
        source = pull_request.head.ref if pull_request.head else ""
        target = pull_request.base.ref if pull_request.base else ""
        author = pull_request.user.login if pull_request.user else "unknown"
        author_name = ""
        if pull_request.user:
            author_name = (pull_request.user.full_name or "").strip()
        return PullRequestSnapshot(
            repository=repository,
            number=number,
            title=pull_request.title,
            description=pull_request.body or "",
            author=author,
            author_name=author_name or author,
            source_branch=source,
            target_branch=target,
            head_sha=head_sha,
            html_url=pull_request.html_url,
            state=pull_request.state,
            merged=pull_request.merged,
            files=files,
            diff=diff,
            commit_count=len(commits),
            opened_at=pull_request.created_at,
            closed_at=pull_request.closed_at,
            merged_at=pull_request.merged_at,
            pull_request=pull_request,
        )

    async def post_or_update_review_comment(
        self,
        repository: str,
        number: int,
        body: str,
    ) -> None:
        await upsert_review_comment(
            provider=self.name,
            repository=repository,
            number=number,
            body=body,
            list_comments=self.client.get_comments,
            create_comment=self.client.create_comment,
            update_comment=lambda repo, _pr, comment_id, marked: self.client.update_comment(
                repo, comment_id, marked
            ),
        )

    async def add_labels(self, repository: str, number: int, labels: list[str]) -> None:
        await self.client.add_labels(repository, number, labels)
