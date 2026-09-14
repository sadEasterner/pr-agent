from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.schemas import AiReviewResult


class AiProvider(ABC):
    name: str

    @abstractmethod
    async def complete_review(self, system_prompt: str, user_prompt: str) -> AiReviewResult:
        """Return a structured review. Repository content is untrusted."""
