from __future__ import annotations

from enum import StrEnum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


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
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    severity: FindingSeverity
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    file: str = Field(default="", validation_alias=AliasChoices("file", "path", "filename", "file_path"))
    line: int | None = None
    category: str = "general"
    rule: str = ""
    message: str = Field(
        default="",
        validation_alias=AliasChoices(
            "message",
            "description",
            "reason",
            "comment",
            "text",
            "details",
            "explanation",
        ),
    )
    suggested_fix: str = Field(
        default="",
        validation_alias=AliasChoices("suggested_fix", "fix", "suggestion", "suggestedFix"),
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: object) -> float:
        if value is None or value == "":
            return 0.8
        try:
            numeric = float(str(value))
        except (TypeError, ValueError):
            return 0.8
        return max(0.0, min(1.0, numeric))

    @field_validator("message", mode="before")
    @classmethod
    def coerce_message(cls, value: object) -> object:
        return "" if value is None else value


class AiReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    risk: RiskLevel = RiskLevel.UNKNOWN
    recommendation: Recommendation
    summary: str = "AI review completed."
    findings: list[AiFinding] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def fill_missing_review_fields(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if not payload.get("summary"):
            payload["summary"] = payload.get("overview") or payload.get("analysis") or "AI review completed."
        if not payload.get("risk"):
            severities = {
                str((item or {}).get("severity", "")).lower()
                for item in payload.get("findings") or []
                if isinstance(item, dict)
            }
            if "critical" in severities:
                payload["risk"] = RiskLevel.CRITICAL
            elif "high" in severities:
                payload["risk"] = RiskLevel.HIGH
            elif "medium" in severities:
                payload["risk"] = RiskLevel.MEDIUM
            elif "low" in severities:
                payload["risk"] = RiskLevel.LOW
            else:
                payload["risk"] = RiskLevel.LOW
        return payload

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
