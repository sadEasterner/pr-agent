from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.config import Settings

SENSITIVE_KEYS = {
    "authorization",
    "token",
    "access_token",
    "gitea_token",
    "scm_token",
    "openai_api_key",
    "deepseek_api_key",
    "ai_review_api_key",
    "api_key",
    "webhook_secret",
    "gitea_webhook_secret",
    "scm_webhook_secret",
    "password",
    "admin_password",
    "auth_session_secret",
    "secret",
    "database_url",
}


def _redact(value: Any, key: str | None = None) -> Any:
    if key and key.lower() in SENSITIVE_KEYS:
        return "[redacted]"
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def drop_sensitive_data(
    _logger: logging.Logger, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    return {key: _redact(value, key) for key, value in event_dict.items()}


def configure_logging(settings: Settings) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        drop_sensitive_data,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.app_env == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
