from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.scm.models import PullRequestSnapshot

SUPPORTED_PROVIDERS = ("gitea", "github", "gitlab")
PROVIDER_LABELS = {
    "gitea": "Gitea",
    "forgejo": "Forgejo",
    "github": "GitHub",
    "gitlab": "GitLab",
}


class ScmError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@runtime_checkable
class ScmProvider(Protocol):
    """Git host adapter. Implementations must never merge, approve, close, or push."""

    name: str

    async def close(self) -> None: ...

    async def fetch_snapshot(self, repository: str, number: int) -> PullRequestSnapshot: ...

    async def post_or_update_review_comment(
        self,
        repository: str,
        number: int,
        body: str,
    ) -> None: ...

    async def add_labels(self, repository: str, number: int, labels: list[str]) -> None: ...


def normalize_provider(value: str) -> str:
    name = (value or "gitea").lower().strip()
    aliases = {
        "gh": "github",
        "github.com": "github",
        "gl": "gitlab",
        "gitlab.com": "gitlab",
        "forgejo": "gitea",
        "codeberg": "gitea",
    }
    return aliases.get(name, name)


def provider_label(value: str) -> str:
    name = normalize_provider(value)
    return PROVIDER_LABELS.get(name, name.title() or "Git host")
