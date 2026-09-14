from __future__ import annotations

from app.config import Settings
from app.gitea.client import GiteaClient
from app.gitea.service import GiteaService
from app.scm.base import ScmError, ScmProvider, normalize_provider
from app.scm.github import GitHubProvider
from app.scm.gitlab import GitLabProvider


def create_scm_provider(settings: Settings) -> ScmProvider:
    provider = normalize_provider(settings.scm_provider)
    if provider == "github":
        return GitHubProvider(settings)
    if provider == "gitlab":
        return GitLabProvider(settings)
    if provider == "gitea":
        return GiteaService(GiteaClient(settings))
    raise ScmError(
        f"Unsupported SCM_PROVIDER '{settings.scm_provider}'. Use gitea, github, or gitlab."
    )
