from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FileChange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    filename: str
    status: str = "modified"
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None
    raw_url: str | None = None


class Comment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    body: str = ""


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
    files: list[FileChange]
    diff: str
    commit_count: int
    opened_at: datetime | str | None = None
    closed_at: datetime | str | None = None
    merged_at: datetime | str | None = None
    pull_request: Any = None
