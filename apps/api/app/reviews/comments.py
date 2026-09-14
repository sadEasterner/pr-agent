from __future__ import annotations

from collections import Counter

from app.ai.schemas import AiReviewResult
from app.gitea.service import PullRequestSnapshot
from app.policy.engine import PolicyEngine
from app.rules.engine import RulesResult


def render_gitea_review(
    snapshot: PullRequestSnapshot,
    rules_result: RulesResult,
    ai_result: AiReviewResult,
    policy: PolicyEngine,
) -> str:
    counts = Counter(finding.severity.value for finding in ai_result.findings)
    human_label = policy.human_label(ai_result.recommendation.value)
    lines = [
        "🤖 Automated PR Review",
        "",
        f"Risk: {ai_result.risk.value.title()}",
        "",
        f"Critical: {counts.get('critical', 0)}",
        f"High: {counts.get('high', 0)}",
        f"Medium: {counts.get('medium', 0)}",
        f"Low: {counts.get('low', 0)}",
        "",
    ]
    notable = [
        finding
        for finding in ai_result.findings
        if finding.severity.value in {"critical", "high", "medium"}
    ][:8]
    if notable:
        lines.append("Findings:")
        for finding in notable:
            location = finding.file
            if finding.line:
                location = f"{finding.file}:{finding.line}"
            lines.extend(
                [
                    "",
                    f"[{finding.severity.value.upper()}] {location}",
                    finding.message,
                    f"Rule: {finding.rule or finding.category}",
                    f"Suggested fix: {finding.suggested_fix or 'See the dashboard for details.'}",
                    f"Confidence: {round(finding.confidence * 100)}%",
                ]
            )
        lines.append("")
    if rules_result.labels:
        lines.append(f"Suggested labels: {', '.join(rules_result.labels)}")
    if rules_result.suggested_reviewers:
        lines.append(f"Suggested reviewers: {', '.join(rules_result.suggested_reviewers)}")
    lines.extend(
        [
            "",
            "Recommendation:",
            human_label + ".",
            "",
            "Merge authority:",
            "Human approval required. The AI reviewer cannot approve or merge.",
            "",
            "Head commit:",
            snapshot.head_sha,
        ]
    )
    return "\n".join(lines)
