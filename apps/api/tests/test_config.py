from pydantic import ValidationError

from app.config import Settings, get_settings


def test_production_requires_gitea_secrets() -> None:
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
