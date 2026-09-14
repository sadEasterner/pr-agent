from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookRepository(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str = ""
    name: str = ""
    owner: dict[str, Any] | None = None
    html_url: str = ""

    @property
    def repository(self) -> str:
        if self.full_name:
            return self.full_name
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


class GiteaWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: str = ""
    number: int | None = None
    pull_request: WebhookPullRequest | None = None
    repository: WebhookRepository | None = None
    sender: WebhookUser | None = None
    commits: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("action")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        return value.lower().strip()

    @property
    def event_type(self) -> str:
        if self.action in {"synchronized", "synchronize"}:
            return "synchronized"
        if self.action in {"opened", "reopened", "edited", "closed", "merged"}:
            if self.action == "closed" and self.pull_request and self.pull_request.merged:
                return "merged"
            return self.action
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
        if self.action in {"closed", "merged"}:
            return True
        pull_request = self.pull_request
        if pull_request is None:
            return False
        if pull_request.merged:
            return True
        return (pull_request.state or "").lower() in {"closed", "merged"}
