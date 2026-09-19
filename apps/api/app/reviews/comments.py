from __future__ import annotations

from app.ai.schemas import AiReviewResult
from app.policy.engine import PolicyEngine
from app.rules.engine import RulesResult
from app.scm.models import PullRequestSnapshot


def render_review(
    snapshot: PullRequestSnapshot,
    rules_result: RulesResult,
    ai_result: AiReviewResult,
    policy: PolicyEngine,
) -> str:
    del snapshot, policy
    suggestions = _suggestions(ai_result, rules_result)
    if not suggestions:
        return "good"
    return "\n".join(f"- {item}" for item in suggestions[:8])


def _suggestions(ai_result: AiReviewResult, rules_result: RulesResult) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        cleaned = text.strip()
        if not cleaned or cleaned.lower() == "good":
            return
        key = cleaned.lower()
        if key in seen:
            return
        seen.add(key)
        items.append(cleaned)

    for item in ai_result.suggestions:
        add(item)
    for finding in ai_result.findings:
        add(finding.suggested_fix or finding.message)
    for violation in rules_result.violations:
        if violation.rule == "workspace_isolation":
            target = violation.files[0] if violation.files else "the extra files"
            add(f"Keep this PR inside one app or package. Remove {target} from the diff.")
        else:
            add(violation.message)
    return items


render_gitea_review = render_review
