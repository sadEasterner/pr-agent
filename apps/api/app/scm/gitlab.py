from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.config import Settings
from app.logging import get_logger
from app.scm.base import ScmError
from app.scm.comments import upsert_review_comment
from app.scm.models import Comment, FileChange, PullRequestSnapshot

logger = get_logger(__name__)


class GitLabProvider:
    name = "gitlab"

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
        if base.endswith("/api/v4"):
            return base
        return f"{base}/api/v4"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "pr-manager/1.0",
        }
        if self._settings.git_token:
            headers["PRIVATE-TOKEN"] = self._settings.git_token
        return headers

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _project_path(self, repository: str) -> str:
        return f"/projects/{quote(repository, safe='')}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.error("gitlab_request_failed", method=method, path=path, error=str(exc))
            raise ScmError(f"GitLab request failed: {exc}") from exc
        if response.status_code >= 400:
            logger.error(
                "gitlab_http_error",
                method=method,
                path=path,
                status_code=response.status_code,
                body=response.text[:500],
            )
            raise ScmError(
                f"GitLab HTTP {response.status_code} for {method} {path}",
                status_code=response.status_code,
            )
        return response

    async def fetch_snapshot(self, repository: str, number: int) -> PullRequestSnapshot:
        mr = await self._request("GET", f"{self._project_path(repository)}/merge_requests/{number}")
        data = mr.json()
        files = await self._changed_files(repository, number)
        diff = "\n".join(file.patch or "" for file in files)
        commits = await self._request(
            "GET",
            f"{self._project_path(repository)}/merge_requests/{number}/commits",
        )
        payload = commits.json()
        commit_payload = payload if isinstance(payload, list) else []
        author = ((data.get("author") or {}).get("username")) or "unknown"
        diff_refs = data.get("diff_refs") or {}
        sha = diff_refs.get("head_sha") or data.get("sha") or ""
        state = data.get("state") or "opened"
        if state == "opened":
            state = "open"
        return PullRequestSnapshot(
            repository=repository,
            number=number,
            title=data.get("title") or "",
            description=data.get("description") or "",
            author=author,
            source_branch=data.get("source_branch") or "",
            target_branch=data.get("target_branch") or "",
            head_sha=sha,
            html_url=data.get("web_url") or "",
            state=state,
            merged=bool(data.get("merged_at")) or state == "merged",
            files=files,
            diff=diff,
            commit_count=len(commit_payload),
            opened_at=data.get("created_at"),
            closed_at=data.get("closed_at"),
            merged_at=data.get("merged_at"),
        )

    async def _changed_files(self, repository: str, number: int) -> list[FileChange]:
        response = await self._request(
            "GET",
            f"{self._project_path(repository)}/merge_requests/{number}/changes",
        )
        payload = response.json()
        changes = payload.get("changes") if isinstance(payload, dict) else payload
        if not isinstance(changes, list):
            return []
        files: list[FileChange] = []
        for item in changes:
            path = item.get("new_path") or item.get("old_path") or ""
            if item.get("new_file"):
                status = "added"
            elif item.get("deleted_file"):
                status = "removed"
            else:
                status = "modified"
            patch = item.get("diff") or ""
            files.append(
                FileChange(
                    filename=path,
                    status=status,
                    additions=max(patch.count("\n+") - patch.count("\n+++"), 0),
                    deletions=max(patch.count("\n-") - patch.count("\n---"), 0),
                    patch=patch,
                )
            )
        return files

    async def list_comments(self, repository: str, number: int) -> list[Comment]:
        response = await self._request(
            "GET",
            f"{self._project_path(repository)}/merge_requests/{number}/notes",
        )
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [Comment.model_validate(item) for item in payload if not item.get("system")]

    async def create_comment(self, repository: str, number: int, body: str) -> Comment:
        response = await self._request(
            "POST",
            f"{self._project_path(repository)}/merge_requests/{number}/notes",
            json={"body": body},
        )
        return Comment.model_validate(response.json())

    async def update_comment(self, repository: str, number: int, comment_id: int, body: str) -> Comment:
        response = await self._request(
            "PUT",
            f"{self._project_path(repository)}/merge_requests/{number}/notes/{comment_id}",
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
            update_comment=self.update_comment,
        )

    async def add_labels(self, repository: str, number: int, labels: list[str]) -> None:
        if not labels:
            return
        await self._request(
            "PUT",
            f"{self._project_path(repository)}/merge_requests/{number}",
            json={"add_labels": ",".join(labels)},
        )
