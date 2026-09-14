from __future__ import annotations

from dataclasses import dataclass

from app.gitea.client import GiteaClient
from app.gitea.models import GiteaFileChange, GiteaPullRequest
from app.logging import get_logger

logger = get_logger(__name__)

REVIEW_MARKER = "PR-MANAGER-REVIEW"


@dataclass
class PullRequestSnapshot:
    repository: str
    number: int
    title: str
    description: str
    author: str
    source_branch: str
    target_branch: str
    head_sha: str
    html_url: str
    state: str
    merged: bool
    files: list[GiteaFileChange]
    diff: str
    commit_count: int
    pull_request: GiteaPullRequest


class GiteaService:
    def __init__(self, client: GiteaClient) -> None:
        self.client = client

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
        return PullRequestSnapshot(
            repository=repository,
            number=number,
            title=pull_request.title,
            description=pull_request.body or "",
            author=author,
            source_branch=source,
            target_branch=target,
            head_sha=head_sha,
            html_url=pull_request.html_url,
            state=pull_request.state,
            merged=pull_request.merged,
            files=files,
            diff=diff,
            commit_count=len(commits),
            pull_request=pull_request,
        )

    async def post_or_update_review_comment(
        self,
        repository: str,
        number: int,
        body: str,
    ) -> None:
        marked_body = f"{REVIEW_MARKER}\n{body}"
        comments = await self.client.get_comments(repository, number)
        existing = next((comment for comment in comments if REVIEW_MARKER in comment.body), None)
        if existing:
            await self.client.update_comment(repository, existing.id, marked_body)
            logger.info(
                "gitea_comment_updated",
                repository=repository,
                pr_number=number,
                comment_id=existing.id,
            )
            return
        await self.client.create_comment(repository, number, marked_body)
        logger.info("gitea_comment_created", repository=repository, pr_number=number)
