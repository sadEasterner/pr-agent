from __future__ import annotations

from fnmatch import fnmatch

from app.ai.base import AiProvider
from app.ai.diff import DiffBundle, prepare_diff_bundle
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.providers.openai import fallback_unable_to_review
from app.ai.schemas import AiFinding, AiReviewResult, FindingSeverity, Recommendation, RiskLevel
from app.config import Settings
from app.gitea.service import PullRequestSnapshot
from app.logging import get_logger
from app.rules.engine import RulesResult
from app.rules.loader import LoadedRules

logger = get_logger(__name__)


class AiReviewer:
    def __init__(
        self,
        settings: Settings,
        loaded_rules: LoadedRules,
        provider: AiProvider | None,
    ) -> None:
        self.settings = settings
        self.loaded_rules = loaded_rules
        self.provider = provider

    async def review(
        self,
        snapshot: PullRequestSnapshot,
        rules_result: RulesResult,
        bundle: DiffBundle | None = None,
        *,
        ai_enabled: bool | None = None,
    ) -> AiReviewResult:
        config = self.loaded_rules.global_rules
        repo_rules = self.loaded_rules.repository_rules.get(snapshot.repository)
        ai_config = config.ai_review
        if repo_rules and repo_rules.ai_review:
            ai_config = repo_rules.ai_review

        enabled = self.settings.ai_enabled if ai_enabled is None else ai_enabled
        if enabled and self.provider is None:
            from app.ai.client import create_ai_provider

            try:
                self.provider = create_ai_provider(self.settings)
            except Exception:
                logger.exception("ai_provider_unavailable")
                return fallback_unable_to_review("The AI provider is not configured.")
        if not enabled or not ai_config.enabled or self.provider is None:
            return self._rules_only_result(rules_result)

        bundle = bundle or prepare_diff_bundle(snapshot.files, snapshot.diff, self.settings)
        if not bundle.chunks:
            return fallback_unable_to_review("No reviewable source diffs were available.")

        project_rules = list(config.project_rules)
        path_rules = {pattern: list(rule.check) for pattern, rule in config.path_rules.items()}
        if repo_rules:
            project_rules.extend(repo_rules.project_rules)
            for pattern, rule in repo_rules.path_rules.items():
                path_rules.setdefault(pattern, []).extend(rule.check)

        applicable_path_rules = {
            pattern: checks
            for pattern, checks in path_rules.items()
            if any(fnmatch(file.filename.replace("\\", "/"), pattern) for file in bundle.files)
        }
        user_prompt = build_user_prompt(
            repository=snapshot.repository,
            pr_number=snapshot.number,
            title=snapshot.title,
            description=snapshot.description,
            author=snapshot.author,
            source_branch=snapshot.source_branch,
            target_branch=snapshot.target_branch,
            head_sha=snapshot.head_sha,
            global_checks=ai_config.check,
            ignore_list=ai_config.ignore,
            project_rules=project_rules,
            path_rules=applicable_path_rules,
            rules_notes=[item.message for item in rules_result.violations],
            diff_chunks=bundle.chunks,
        )
        logger.info(
            "ai_review_start",
            repository=snapshot.repository,
            pr_number=snapshot.number,
            head_sha=snapshot.head_sha,
            files=len(bundle.files),
        )
        try:
            result = await self.provider.complete_review(SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            logger.error("ai_review_failed", error=str(exc))
            return fallback_unable_to_review("The AI provider failed. Human review is required.")

        result.findings = [
            finding
            for finding in result.findings
            if finding.confidence >= ai_config.minimum_confidence
        ]
        result = self._merge_rule_findings(result, rules_result)
        result = self._normalize_recommendation(result)
        logger.info(
            "ai_review_complete",
            repository=snapshot.repository,
            pr_number=snapshot.number,
            head_sha=snapshot.head_sha,
            findings=len(result.findings),
            risk=result.risk,
            recommendation=result.recommendation,
        )
        return result

    def _rules_only_result(self, rules_result: RulesResult) -> AiReviewResult:
        if rules_result.dangerous_changes or rules_result.migration_changes:
            risk = RiskLevel.HIGH
            recommendation = Recommendation.HIGH_RISK
        elif rules_result.violations:
            risk = RiskLevel.MEDIUM
            recommendation = Recommendation.CHANGES_REQUESTED
        else:
            risk = RiskLevel.LOW
            recommendation = Recommendation.READY_FOR_HUMAN_REVIEW
        findings = [
            AiFinding(
                severity=FindingSeverity(violation.severity)
                if violation.severity in FindingSeverity._value2member_map_
                else FindingSeverity.MEDIUM,
                confidence=1.0,
                file=violation.files[0] if violation.files else "",
                line=None,
                category=violation.rule,
                rule=violation.rule,
                message=violation.message,
                suggested_fix="",
            )
            for violation in rules_result.violations
        ]
        return AiReviewResult(
            risk=risk,
            recommendation=recommendation,
            summary="good" if not findings else (findings[0].message or "good"),
            findings=findings,
        )

    def _merge_rule_findings(self, result: AiReviewResult, rules_result: RulesResult) -> AiReviewResult:
        known = {finding.rule for finding in result.findings}
        for violation in rules_result.violations:
            if violation.rule in known:
                continue
            result.findings.append(
                AiFinding(
                    severity=FindingSeverity(violation.severity)
                    if violation.severity in FindingSeverity._value2member_map_
                    else FindingSeverity.MEDIUM,
                    confidence=1.0,
                    file=violation.files[0] if violation.files else "",
                    line=None,
                    category=violation.rule,
                    rule=violation.rule,
                    message=violation.message,
                    suggested_fix=violation.message,
                )
            )
            known.add(violation.rule)
        isolation = [item for item in rules_result.violations if item.rule == "workspace_isolation"]
        if isolation:
            result.recommendation = Recommendation.CHANGES_REQUESTED
            if result.risk in {RiskLevel.LOW, RiskLevel.UNKNOWN}:
                result.risk = RiskLevel.HIGH
            if isolation[0].message not in result.summary:
                result.summary = f"{isolation[0].message} {result.summary}".strip()
        return result

    def _normalize_recommendation(self, result: AiReviewResult) -> AiReviewResult:
        severities = {finding.severity for finding in result.findings}
        if FindingSeverity.CRITICAL in severities:
            result.risk = RiskLevel.CRITICAL
            result.recommendation = Recommendation.HIGH_RISK
        elif FindingSeverity.HIGH in severities:
            result.risk = RiskLevel.HIGH
            result.recommendation = Recommendation.CHANGES_REQUESTED
        elif result.recommendation.value in {"approved", "merged"}:
            result.recommendation = Recommendation.READY_FOR_HUMAN_REVIEW
        return result
