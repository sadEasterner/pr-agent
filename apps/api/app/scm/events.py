from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookRepository(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str = ""
    name: str = ""
    owner: dict[str, Any] | None = None
    html_url: str = ""
    path_with_namespace: str = ""

    @property
    def repository(self) -> str:
        if self.full_name:
            return self.full_name
        if self.path_with_namespace:
            return self.path_with_namespace
        owner_login = ""
        if isinstance(self.owner, dict):
            owner_login = str(self.owner.get("login") or self.owner.get("username") or "")
        if owner_login and self.name:
            return f"{owner_login}/{self.name}"
        return self.name


class WebhookUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str = ""
    username: str = ""

    @property
    def name(self) -> str:
        return self.login or self.username or "unknown"


class WebhookBranch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ref: str = ""
    sha: str = ""
    label: str = ""


class WebhookPullRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    number: int
    title: str = ""
    body: str | None = ""
    html_url: str = ""
    state: str = "open"
    merged: bool = False
    merged_at: str | None = None
    created_at: str | None = None
    closed_at: str | None = None
    user: WebhookUser | None = None
    head: WebhookBranch | None = None
    base: WebhookBranch | None = None
    changed_files: int | None = None


class PullRequestEvent(BaseModel):
    """Normalized pull/merge request webhook. Used by the job queue for every Git host."""

    model_config = ConfigDict(extra="ignore")

    action: str = ""
    number: int | None = None
    pull_request: WebhookPullRequest | None = None
    repository: WebhookRepository | None = None
    sender: WebhookUser | None = None
    commits: list[dict[str, Any]] = Field(default_factory=list)
    provider: str = ""

    @field_validator("action")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        return value.lower().strip()

    @property
    def event_type(self) -> str:
        if self.action in {"synchronized", "synchronize", "update"}:
            return "synchronized"
        if self.action in {"opened", "open", "reopened", "reopen", "edited", "closed", "merged"}:
            action = {"open": "opened", "reopen": "reopened"}.get(self.action, self.action)
            if action == "closed" and self.pull_request and self.pull_request.merged:
                return "merged"
            return action
        return self.action or "unknown"

    @property
    def repository_name(self) -> str:
        if not self.repository:
            return ""
        return self.repository.repository

    @property
    def pr_number(self) -> int | None:
        if self.pull_request:
            return self.pull_request.number
        return self.number

    @property
    def head_sha(self) -> str:
        if self.pull_request and self.pull_request.head:
            return self.pull_request.head.sha
        return ""

    @property
    def is_closed_or_merged(self) -> bool:
        if self.action in {"closed", "merged", "close", "merge"}:
            return True
        pull_request = self.pull_request
        if pull_request is None:
            return False
        if pull_request.merged:
            return True
        return (pull_request.state or "").lower() in {"closed", "merged"}


GiteaWebhookEvent = PullRequestEvent


def parse_gitea_or_github_event(body: bytes, provider: str) -> PullRequestEvent:
    event = PullRequestEvent.model_validate_json(body)
    event.provider = provider
    if event.action == "synchronize":
        event.action = "synchronized"
    return event


def parse_gitlab_event(body: bytes) -> PullRequestEvent:
    data = json.loads(body)
    attrs = data.get("object_attributes") or {}
    project = data.get("project") or {}
    user = data.get("user") or {}
    action = str(attrs.get("action") or "").lower()
    action_map = {
        "open": "opened",
        "reopen": "reopened",
        "update": "synchronized",
        "close": "closed",
        "merge": "merged",
    }
    state = str(attrs.get("state") or "opened").lower()
    if state == "opened":
        state = "open"
    last_commit = attrs.get("last_commit") or {}
    sha = str(last_commit.get("id") or attrs.get("sha") or "")
    iid = attrs.get("iid") or attrs.get("id")
    merged = bool(attrs.get("merged_at")) or action == "merge" or state == "merged"
    return PullRequestEvent(
        action=action_map.get(action, action),
        number=iid,
        provider="gitlab",
        pull_request=WebhookPullRequest(
            number=int(iid or 0),
            title=attrs.get("title") or "",
            body=attrs.get("description") or "",
            html_url=attrs.get("url") or attrs.get("web_url") or "",
            state="merged" if merged else state,
            merged=merged,
            merged_at=attrs.get("merged_at"),
            created_at=attrs.get("created_at"),
            closed_at=attrs.get("closed_at"),
            user=WebhookUser(login=user.get("username") or user.get("name") or ""),
            head=WebhookBranch(ref=attrs.get("source_branch") or "", sha=sha),
            base=WebhookBranch(ref=attrs.get("target_branch") or ""),
        ),
        repository=WebhookRepository(
            full_name=project.get("path_with_namespace") or "",
            name=project.get("name") or "",
            path_with_namespace=project.get("path_with_namespace") or "",
        ),
        sender=WebhookUser(login=user.get("username") or ""),
    )


def parse_webhook_event(provider: str, body: bytes) -> PullRequestEvent:
    if provider == "gitlab":
        return parse_gitlab_event(body)
    return parse_gitea_or_github_event(body, provider)
