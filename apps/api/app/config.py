from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    max_request_bytes: int = 2_000_000

    database_url: str = "postgresql+asyncpg://prmanager:prmanager@localhost:5432/prmanager"

    gitea_base_url: str = "https://gitea.example.com"
    gitea_token: str = ""
    gitea_webhook_secret: str = ""
    gitea_api_timeout_seconds: float = 30.0

    ai_enabled: bool = False
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    deepseek_api_key: str = ""
    ai_timeout_seconds: float = 60.0
    ai_max_diff_chars: int = 80_000
    ai_max_files: int = 40
    ai_chunk_size: int = 12_000

    config_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "config")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://") and "+asyncpg" not in value:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @model_validator(mode="after")
    def require_production_secrets(self) -> "Settings":
        if not self.is_production:
            return self
        missing: list[str] = []
        if not self.gitea_webhook_secret:
            missing.append("GITEA_WEBHOOK_SECRET")
        if not self.gitea_token:
            missing.append("GITEA_TOKEN")
        if not self.gitea_base_url or "example.com" in self.gitea_base_url:
            missing.append("GITEA_BASE_URL")
        if missing:
            raise ValueError("Production requires " + ", ".join(missing))
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def review_rules_path(self) -> Path:
        return self.config_dir / "review-rules.yaml"

    @property
    def repository_rules_dir(self) -> Path:
        return self.config_dir / "repositories"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def ai_review_api_key(self) -> str:
        """Key used only by the PR reviewer. Never sent to Gitea or other services."""
        if self.ai_provider.lower().strip() == "deepseek":
            return self.deepseek_api_key
        return self.openai_api_key

    @property
    def ai_review_base_url(self) -> str:
        provider = self.ai_provider.lower().strip()
        if provider == "deepseek":
            if not self.openai_base_url or "api.openai.com" in self.openai_base_url:
                return "https://api.deepseek.com/v1"
        return self.openai_base_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
