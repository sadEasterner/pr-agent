from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.scm.models import FileChange


class GiteaUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str = ""
    id: int | None = None
    full_name: str = ""


class GiteaRepository(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    name: str = ""
    full_name: str = ""
    html_url: str = ""
    clone_url: str = ""
    default_branch: str = ""
    owner: GiteaUser | None = None


class GiteaBranchRef(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ref: str = ""
    sha: str = ""
    label: str = ""
    repo: GiteaRepository | None = None


class GiteaPullRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    number: int
    title: str = ""
    body: str | None = ""
    state: str = "open"
    html_url: str = ""
    mergeable: bool | None = None
    merged: bool = False
    merged_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    user: GiteaUser | None = None
    head: GiteaBranchRef | None = None
    base: GiteaBranchRef | None = None
    labels: list[dict[str, Any]] = Field(default_factory=list)


class GiteaFileChange(FileChange):
    """File payload shared with GitHub-style APIs."""


class GiteaCommit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sha: str
    message: str = ""
    author_name: str = ""
    created: datetime | None = None


class GiteaComment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    body: str = ""
    user: GiteaUser | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GiteaStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    status: str = ""
    context: str = ""
    description: str = ""
    target_url: str = ""


class GiteaWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: str = ""
    number: int | None = None
    pull_request: GiteaPullRequest | None = None
    repository: GiteaRepository | None = None
    sender: GiteaUser | None = None
