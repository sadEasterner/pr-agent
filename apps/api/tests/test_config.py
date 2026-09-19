from app.config import Settings, get_settings
from pydantic import ValidationError


def test_production_requires_scm_secrets() -> None:
    get_settings.cache_clear()
    try:
        Settings(
            app_env="production",
            gitea_base_url="https://git.example.org",
            gitea_token="token",
            gitea_webhook_secret="",
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_github_production_uses_public_api_default() -> None:
    get_settings.cache_clear()
    settings = Settings(
        app_env="production",
        scm_provider="github",
        scm_token="gh-token",
        scm_webhook_secret="hook-secret",
        admin_username="admin",
        admin_password="admin-password",
        auth_session_secret="session-secret-not-for-production",
    )
    assert settings.git_base_url == "https://api.github.com"
    assert settings.git_provider == "github"


def test_production_requires_admin_credentials() -> None:
    get_settings.cache_clear()
    try:
        Settings(
            app_env="production",
            gitea_base_url="https://git.example.org",
            gitea_token="token",
            gitea_webhook_secret="secret",
            admin_username="",
            admin_password="",
            auth_session_secret="session-secret",
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
    get_settings.cache_clear()
    settings = Settings(
        app_env="test",
        gitea_webhook_secret="",
        gitea_token="",
    )
    assert settings.is_production is False
