from __future__ import annotations

from app.ai.base import AiProvider
from app.ai.providers.openai import OpenAIProvider
from app.config import Settings


class UnsupportedAiProviderError(ValueError):
    pass


def create_ai_provider(settings: Settings, client: object | None = None) -> AiProvider:
    provider = settings.ai_provider.lower().strip()
    if provider in {"openai", "openai_compatible", "deepseek"}:
        return OpenAIProvider(settings, client=client)  # type: ignore[arg-type]
    raise UnsupportedAiProviderError(
        f"Unsupported AI provider '{settings.ai_provider}'. "
        "Add a new implementation under app/ai/providers without changing PR management logic."
    )
