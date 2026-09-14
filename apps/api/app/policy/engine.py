from __future__ import annotations

from enum import StrEnum

from app.rules.loader import AutomationConfig


class AutomationAction(StrEnum):
    READ_PR = "read_pr"
    READ_DIFF = "read_diff"
    POST_REVIEW = "post_review"
    ADD_LABELS = "add_labels"
    RECOMMEND_MERGE = "recommend_merge"
    REQUEST_HUMAN_REVIEW = "request_human_review"
    MERGE_PR = "merge_pr"
    APPROVE_PR = "approve_pr"
    CLOSE_PR = "close_pr"
    PUSH_CODE = "push_code"
    MODIFY_REPOSITORY = "modify_repository"


NEVER_ALLOWED = {
    AutomationAction.MERGE_PR,
    AutomationAction.APPROVE_PR,
    AutomationAction.CLOSE_PR,
    AutomationAction.PUSH_CODE,
    AutomationAction.MODIFY_REPOSITORY,
}

HUMAN_STATUS = {
    "ready_for_human_review": "waiting_for_human",
    "changes_requested": "changes_requested",
    "high_risk": "high_risk",
    "unable_to_review": "unable_to_review",
}

HUMAN_LABELS = {
    "ready_for_human_review": "READY FOR HUMAN REVIEW",
    "changes_requested": "CHANGES REQUESTED",
    "high_risk": "HIGH RISK",
    "unable_to_review": "UNABLE TO REVIEW",
}


class PolicyEngine:
    def __init__(self, config: AutomationConfig) -> None:
        self.config = config
        self.allowed = set(config.allowed_actions)
        self.forbidden = set(config.forbidden_actions) | {item.value for item in NEVER_ALLOWED}

    def can(self, action: AutomationAction | str) -> bool:
        value = action.value if isinstance(action, AutomationAction) else action
        if value in self.forbidden or value in {item.value for item in NEVER_ALLOWED}:
            return False
        if self.config.mode != "review_only":
            return False
        return value in self.allowed

    def translate_recommendation(self, recommendation: str) -> str:
        return HUMAN_STATUS.get(recommendation, "waiting_for_human")

    def human_label(self, recommendation: str) -> str:
        return HUMAN_LABELS.get(recommendation, "READY FOR HUMAN REVIEW")

    def assert_not_merge_authority(self, recommendation: str) -> str:
        """AI merge-like language is always reduced to a human-review state."""
        if recommendation in {"approved", "merged", "approve", "merge"}:
            return "waiting_for_human"
        return self.translate_recommendation(recommendation)
