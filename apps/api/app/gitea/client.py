from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.gitea.models import (
    GiteaComment,
    GiteaCommit,
    GiteaFileChange,
    GiteaPullRequest,
    GiteaRepository,
    GiteaStatus,
)
from app.logging import get_logger

logger = get_logger(__name__)


class GiteaClientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GiteaClient:
    """Isolated HTTP client for Gitea API v1."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = client is None
        timeout = httpx.Timeout(settings.gitea_api_timeout_seconds)
        self._client = client or httpx.AsyncClient(
            base_url=settings.gitea_base_url.rstrip("/"),
            timeout=timeout,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "gitea-pr-manager/1.0",
        }
        if self._settings.gitea_token:
            headers["Authorization"] = f"token {self._settings.gitea_token}"
        return headers

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.error("gitea_request_failed", method=method, path=path, error=str(exc))
            raise GiteaClientError(f"Gitea request failed: {exc}") from exc
        if response.status_code >= 400:
            logger.error(
                "gitea_http_error",
                method=method,
                path=path,
                status_code=response.status_code,
            )
            raise GiteaClientError(
                f"Gitea HTTP {response.status_code} for {method} {path}",
                status_code=response.status_code,
            )
        return response

    def _owner_repo_path(self, repository: str) -> str:
        if "/" not in repository:
            raise GiteaClientError(f"Invalid repository name: {repository}")
        owner, repo = repository.split("/", 1)
        return f"/api/v1/repos/{owner}/{repo}"

    async def get_repository(self, repository: str) -> GiteaRepository:
        path = self._owner_repo_path(repository)
        response = await self._request("GET", path)
        return GiteaRepository.model_validate(response.json())

    async def get_pull_request(self, repository: str, number: int) -> GiteaPullRequest:
        path = f"{self._owner_repo_path(repository)}/pulls/{number}"
        response = await self._request("GET", path)
        return GiteaPullRequest.model_validate(response.json())

    async def get_changed_files(self, repository: str, number: int) -> list[GiteaFileChange]:
        path = f"{self._owner_repo_path(repository)}/pulls/{number}/files"
        response = await self._request("GET", path)
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [GiteaFileChange.model_validate(item) for item in payload]

    async def get_diff(self, repository: str, number: int) -> str:
        path = f"{self._owner_repo_path(repository)}/pulls/{number}.diff"
        response = await self._request(
            "GET",
            path,
            headers={"Accept": "text/plain"},
        )
        return response.text

    async def get_commits(self, repository: str, number: int) -> list[GiteaCommit]:
        path = f"{self._owner_repo_path(repository)}/pulls/{number}/commits"
        response = await self._request("GET", path)
        payload = response.json()
        commits: list[GiteaCommit] = []
        if not isinstance(payload, list):
            return commits
        for item in payload:
            sha = item.get("sha") or item.get("id") or ""
            commit = item.get("commit") or {}
            commits.append(
                GiteaCommit(
                    sha=sha,
                    message=commit.get("message") or item.get("message") or "",
                    author_name=(commit.get("author") or {}).get("name", ""),
                    created=commit.get("committer", {}).get("date"),
                )
            )
        return commits

    async def get_statuses(self, repository: str, sha: str) -> list[GiteaStatus]:
        path = f"{self._owner_repo_path(repository)}/statuses/{sha}"
        response = await self._request("GET", path)
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [GiteaStatus.model_validate(item) for item in payload]

    async def get_comments(self, repository: str, number: int) -> list[GiteaComment]:
        path = f"{self._owner_repo_path(repository)}/issues/{number}/comments"
        response = await self._request("GET", path)
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [GiteaComment.model_validate(item) for item in payload]

    async def create_comment(self, repository: str, number: int, body: str) -> GiteaComment:
        path = f"{self._owner_repo_path(repository)}/issues/{number}/comments"
        response = await self._request("POST", path, json={"body": body})
        return GiteaComment.model_validate(response.json())

    async def update_comment(self, repository: str, comment_id: int, body: str) -> GiteaComment:
        path = f"{self._owner_repo_path(repository)}/issues/comments/{comment_id}"
        response = await self._request("PATCH", path, json={"body": body})
        return GiteaComment.model_validate(response.json())

    async def add_labels(self, repository: str, number: int, labels: list[str]) -> None:
        if not labels:
            return
        path = f"{self._owner_repo_path(repository)}/issues/{number}/labels"
        await self._request("POST", path, json={"labels": labels})

    async def remove_labels(self, repository: str, number: int, labels: list[str]) -> None:
        for label in labels:
            path = f"{self._owner_repo_path(repository)}/issues/{number}/labels/{label}"
            await self._request("DELETE", path)

    async def request_reviewers(self, repository: str, number: int, reviewers: list[str]) -> None:
        if not reviewers:
            return
        path = f"{self._owner_repo_path(repository)}/pulls/{number}/requested_reviewers"
        await self._request("POST", path, json={"reviewers": reviewers})

    async def inspect_head_sha(self, repository: str, number: int) -> str:
        pull_request = await self.get_pull_request(repository, number)
        if not pull_request.head or not pull_request.head.sha:
            raise GiteaClientError("PR is missing a head SHA")
        return pull_request.head.sha
