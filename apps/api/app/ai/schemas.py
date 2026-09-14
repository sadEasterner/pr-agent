from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class Recommendation(StrEnum):
    READY_FOR_HUMAN_REVIEW = "ready_for_human_review"
    CHANGES_REQUESTED = "changes_requested"
    HIGH_RISK = "high_risk"
    UNABLE_TO_REVIEW = "unable_to_review"


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AiFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")

    severity: FindingSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    file: str = ""
    line: int | None = None
    category: str
    rule: str = ""
    message: str
    suggested_fix: str = ""

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: object) -> float:
        try:
            numeric = float(str(value))
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, numeric))


class AiReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk: RiskLevel
    recommendation: Recommendation
    summary: str
    findings: list[AiFinding] = Field(default_factory=list)

    @field_validator("recommendation", mode="before")
    @classmethod
    def reject_authoritative_recommendations(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower().replace(" ", "_")
            if normalized in {"approved", "approve", "merged", "merge"}:
                return Recommendation.READY_FOR_HUMAN_REVIEW
            return normalized
        return value

    @field_validator("risk", mode="before")
    @classmethod
    def normalize_risk(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


ALLOWED_RECOMMENDATIONS = {
    Recommendation.READY_FOR_HUMAN_REVIEW,
    Recommendation.CHANGES_REQUESTED,
    Recommendation.HIGH_RISK,
    Recommendation.UNABLE_TO_REVIEW,
}
