from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.logging import get_logger
from app.scm.base import ScmError
from app.scm.comments import upsert_review_comment
from app.scm.models import Comment, FileChange, PullRequestSnapshot

logger = get_logger(__name__)


class GitHubProvider:
    name = "github"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._owns_client = client is None
        timeout = httpx.Timeout(settings.scm_timeout)
        self._client = client or httpx.AsyncClient(
            base_url=self._api_root(),
            timeout=timeout,
            headers=self._headers(),
        )

    def _api_root(self) -> str:
        base = self._settings.git_base_url.rstrip("/")
        if "api.github.com" in base or base.endswith("/api/v3"):
            return base
        return f"{base}/api/v3"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pr-manager/1.0",
        }
        if self._settings.git_token:
            headers["Authorization"] = f"Bearer {self._settings.git_token}"
        return headers

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _repo_path(self, repository: str) -> str:
        if "/" not in repository:
            raise ScmError(f"Invalid repository name: {repository}")
        owner, repo = repository.split("/", 1)
        return f"/repos/{owner}/{repo}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.error("github_request_failed", method=method, path=path, error=str(exc))
            raise ScmError(f"GitHub request failed: {exc}") from exc
        if response.status_code >= 400:
            logger.error(
                "github_http_error",
                method=method,
                path=path,
                status_code=response.status_code,
                body=response.text[:500],
            )
            raise ScmError(
                f"GitHub HTTP {response.status_code} for {method} {path}",
                status_code=response.status_code,
            )
        return response

    async def fetch_snapshot(self, repository: str, number: int) -> PullRequestSnapshot:
        pr = await self._request("GET", f"{self._repo_path(repository)}/pulls/{number}")
        data = pr.json()
        files = await self._changed_files(repository, number)
        try:
            diff_response = await self._request(
                "GET",
                f"{self._repo_path(repository)}/pulls/{number}",
                headers={"Accept": "application/vnd.github.diff"},
            )
            diff = diff_response.text
        except Exception:
            logger.warning("github_diff_unavailable", repository=repository, pr_number=number)
            diff = "\n".join(file.patch or "" for file in files)
        commits = await self._request("GET", f"{self._repo_path(repository)}/pulls/{number}/commits")
        commit_payload = commits.json()
        if not isinstance(commit_payload, list):
            commit_payload = []
        head = data.get("head") or {}
        base = data.get("base") or {}
        user = data.get("user") or {}
        author = user.get("login") or "unknown"
        author_name = (user.get("name") or user.get("full_name") or "").strip()
        if not author_name:
            for commit in commit_payload:
                commit_author = ((commit.get("commit") or {}).get("author") or {}).get("name")
                if commit_author:
                    author_name = str(commit_author).strip()
                    break
        return PullRequestSnapshot(
            repository=repository,
            number=number,
            title=data.get("title") or "",
            description=data.get("body") or "",
            author=author,
            author_name=author_name or author,
            source_branch=head.get("ref") or "",
            target_branch=base.get("ref") or "",
            head_sha=head.get("sha") or "",
            html_url=data.get("html_url") or "",
            state=data.get("state") or "open",
            merged=bool(data.get("merged")),
            files=files,
            diff=diff,
            commit_count=len(commit_payload),
            opened_at=data.get("created_at"),
            closed_at=data.get("closed_at"),
            merged_at=data.get("merged_at"),
        )

    async def _changed_files(self, repository: str, number: int) -> list[FileChange]:
        files: list[FileChange] = []
        page = 1
        while page <= 10:
            response = await self._request(
                "GET",
                f"{self._repo_path(repository)}/pulls/{number}/files",
                params={"per_page": 100, "page": page},
            )
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                break
            files.extend(FileChange.model_validate(item) for item in payload)
            if len(payload) < 100:
                break
            page += 1
        return files

    async def list_comments(self, repository: str, number: int) -> list[Comment]:
        response = await self._request("GET", f"{self._repo_path(repository)}/issues/{number}/comments")
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [Comment.model_validate(item) for item in payload]

    async def create_comment(self, repository: str, number: int, body: str) -> Comment:
        response = await self._request(
            "POST",
            f"{self._repo_path(repository)}/issues/{number}/comments",
            json={"body": body},
        )
        return Comment.model_validate(response.json())

    async def update_comment(self, repository: str, comment_id: int, body: str) -> Comment:
        response = await self._request(
            "PATCH",
            f"{self._repo_path(repository)}/issues/comments/{comment_id}",
            json={"body": body},
        )
        return Comment.model_validate(response.json())

    async def post_or_update_review_comment(self, repository: str, number: int, body: str) -> None:
        await upsert_review_comment(
            provider=self.name,
            repository=repository,
            number=number,
            body=body,
            list_comments=self.list_comments,
            create_comment=self.create_comment,
            update_comment=lambda repo, _number, comment_id, marked: self.update_comment(
                repo, comment_id, marked
            ),
        )

    async def add_labels(self, repository: str, number: int, labels: list[str]) -> None:
        if not labels:
            return
        await self._request(
            "POST",
            f"{self._repo_path(repository)}/issues/{number}/labels",
            json={"labels": labels},
        )
