from __future__ import annotations

from app.ai.schemas import AiReviewResult
from app.scm.models import PullRequestSnapshot
from app.policy.engine import PolicyEngine
from app.rules.engine import RulesResult


def render_review(
    snapshot: PullRequestSnapshot,
    rules_result: RulesResult,
    ai_result: AiReviewResult,
    policy: PolicyEngine,
) -> str:
    del policy
    paragraph = (ai_result.summary or "").strip()
    if not paragraph:
        paragraph = _paragraph_from_findings(ai_result, rules_result)
    suggestions = [item.strip() for item in ai_result.suggestions if item.strip()]
    if not suggestions:
        suggestions = [
            finding.suggested_fix.strip()
            for finding in ai_result.findings
            if finding.suggested_fix.strip()
        ]
    for violation in rules_result.violations:
        if violation.rule == "workspace_isolation":
            target = violation.files[0] if violation.files else "the extra files"
            suggestions.append(f"Keep this PR inside one app or package. Remove {target} from the diff.")
    lines = [
        "Automated PR Review",
        "",
        paragraph,
    ]
    if suggestions:
        lines.extend(["", "Suggestions:"])
        for item in suggestions[:8]:
            lines.append(f"- {item}")
    lines.extend(["", "Head commit:", snapshot.head_sha])
    return "\n".join(lines)


def _paragraph_from_findings(ai_result: AiReviewResult, rules_result: RulesResult) -> str:
    if rules_result.violations:
        return " ".join(item.message for item in rules_result.violations[:3])
    if ai_result.findings:
        return " ".join(item.message for item in ai_result.findings[:3])
    return "The diff does not show a defect in the edited behavior."


render_gitea_review = render_review
