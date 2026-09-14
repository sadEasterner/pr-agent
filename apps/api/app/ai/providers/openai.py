from __future__ import annotations

import json
from typing import Any

import httpx

from app.ai.base import AiProvider
from app.ai.schemas import AiReviewResult, Recommendation, RiskLevel
from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AiProvider):
    name = "openai"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self.name = settings.ai_provider.lower().strip() or "openai"
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.ai_review_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.ai_timeout_seconds),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete_review(self, system_prompt: str, user_prompt: str) -> AiReviewResult:
        api_key = self._settings.ai_review_api_key
        if not api_key:
            raise RuntimeError("AI reviewer API key is not configured")
        payload = {
            "model": self._settings.ai_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            response = await self._client.post(
                "/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("ai_provider_failed", provider=self.name, error=str(exc))
            raise RuntimeError("AI provider request failed") from exc
        data = response.json()
        content = _extract_content(data)
        return parse_ai_payload(content)


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("AI provider returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI provider returned empty content")
    return content


def parse_ai_payload(content: str) -> AiReviewResult:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end < 0:
            raise
        payload = json.loads(content[start : end + 1])
    return AiReviewResult.model_validate(payload)


def fallback_unable_to_review(reason: str) -> AiReviewResult:
    return AiReviewResult(
        risk=RiskLevel.UNKNOWN,
        recommendation=Recommendation.UNABLE_TO_REVIEW,
        summary=reason,
        findings=[],
    )
