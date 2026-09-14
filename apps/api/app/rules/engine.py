from __future__ import annotations

from fnmatch import fnmatch
from typing import Any

from pydantic import BaseModel, Field

from app.gitea.models import GiteaFileChange
from app.gitea.service import PullRequestSnapshot
from app.rules.loader import LoadedRules, PrRulesConfig


class RuleViolation(BaseModel):
    rule: str
    message: str
    severity: str = "medium"
    files: list[str] = Field(default_factory=list)


class RulesResult(BaseModel):
    violations: list[RuleViolation] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    suggested_reviewers: list[str] = Field(default_factory=list)
    large_pr: bool = False
    missing_description: bool = False
    dangerous_changes: bool = False
    migration_changes: bool = False
    infrastructure_changes: bool = False
    test_changes: bool = False
    changed_modules: list[str] = Field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    changed_files: int = 0

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


def _matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        fnmatch(normalized, pattern) or fnmatch(normalized, f"**/{pattern}")
        for pattern in patterns
    )


def _matching_files(files: list[GiteaFileChange], patterns: list[str]) -> list[str]:
    return [file.filename for file in files if _matches(file.filename, patterns)]


def workspace_scope(filename: str) -> str | None:
    parts = [part for part in filename.replace("\\", "/").split("/") if part]
    if len(parts) >= 2 and parts[0] in {"apps", "packages"}:
        return f"{parts[0]}/{parts[1]}"
    return None


class RulesEngine:
    def __init__(self, loaded: LoadedRules) -> None:
        self.loaded = loaded

    def evaluate(self, snapshot: PullRequestSnapshot) -> RulesResult:
        config = self.loaded.global_rules.pr_rules
        files = snapshot.files
        result = RulesResult(
            changed_files=len(files),
            lines_added=sum(file.additions for file in files),
            lines_removed=sum(file.deletions for file in files),
        )
        self._check_description(snapshot, config, result)
        self._check_size(files, config, result)
        self._check_workspace_isolation(files, config, result)
        self._check_path_groups(files, config, result)
        self._assign_labels(files, config, result)
        self._suggest_reviewers(files, config, result)
        result.changed_modules = sorted(
            {file.filename.split("/")[0] for file in files if "/" in file.filename}
        )
        return result

    def _check_description(
        self,
        snapshot: PullRequestSnapshot,
        config: PrRulesConfig,
        result: RulesResult,
    ) -> None:
        description = (snapshot.description or "").strip()
        if config.require_description and len(description) < config.min_description_length:
            result.missing_description = True
            result.violations.append(
                RuleViolation(
                    rule="require_description",
                    message="Pull request is missing a meaningful description.",
                    severity="medium",
                )
            )

    def _check_size(
        self,
        files: list[GiteaFileChange],
        config: PrRulesConfig,
        result: RulesResult,
    ) -> None:
        changed_lines = sum(file.additions + file.deletions for file in files)
        if changed_lines > config.max_changed_lines or len(files) > config.max_changed_files:
            result.large_pr = True
            result.violations.append(
                RuleViolation(
                    rule="max_changed_lines",
                    message=(
                        f"PR is large ({len(files)} files, {changed_lines} changed lines)."
                    ),
                    severity="medium",
                )
            )

    def _check_path_groups(
        self,
        files: list[GiteaFileChange],
        config: PrRulesConfig,
        result: RulesResult,
    ) -> None:
        dangerous = _matching_files(files, config.dangerous_paths)
        if dangerous:
            result.dangerous_changes = True
            result.violations.append(
                RuleViolation(
                    rule="dangerous_file_changes",
                    message="PR changes infrastructure, secrets, or CI configuration files.",
                    severity="high",
                    files=dangerous,
                )
            )
        migrations = _matching_files(files, config.migration_paths)
        if migrations:
            result.migration_changes = True
            result.violations.append(
                RuleViolation(
                    rule="database_migrations",
                    message="PR includes database migration files. Confirm rollback safety.",
                    severity="high",
                    files=migrations,
                )
            )
        infra = _matching_files(files, config.infrastructure_paths)
        if infra:
            result.infrastructure_changes = True
            result.violations.append(
                RuleViolation(
                    rule="infrastructure_changes",
                    message="PR includes infrastructure or deployment changes.",
                    severity="medium",
                    files=infra,
                )
            )
        tests = _matching_files(files, config.test_paths)
        result.test_changes = bool(tests)

    def _check_workspace_isolation(
        self,
        files: list[GiteaFileChange],
        config: PrRulesConfig,
        result: RulesResult,
    ) -> None:
        if not config.enforce_workspace_isolation or not files:
            return
        scopes: dict[str, list[str]] = {}
        outsiders: list[str] = []
        for file in files:
            scope = workspace_scope(file.filename)
            if scope is None:
                outsiders.append(file.filename)
                continue
            scopes.setdefault(scope, []).append(file.filename)
        if len(scopes) > 1:
            names = ", ".join(sorted(scopes))
            result.violations.append(
                RuleViolation(
                    rule="workspace_isolation",
                    message=(
                        "This PR changes more than one app or package "
                        f"({names}). Keep the diff inside a single workspace folder."
                    ),
                    severity="high",
                    files=[path for paths in scopes.values() for path in paths],
                )
            )
            return
        if len(scopes) == 1 and outsiders:
            scope = next(iter(scopes))
            result.violations.append(
                RuleViolation(
                    rule="workspace_isolation",
                    message=(
                        f"This PR is for {scope} but also changes files outside that folder. "
                        "Remove those files from the PR."
                    ),
                    severity="high",
                    files=outsiders,
                )
            )

    def _assign_labels(
        self,
        files: list[GiteaFileChange],
        config: PrRulesConfig,
        result: RulesResult,
    ) -> None:
        labels: list[str] = []
        for name, rule in config.labels.items():
            if _matching_files(files, rule.paths):
                labels.append(name)
        result.labels = sorted(set(labels))

    def _suggest_reviewers(
        self,
        files: list[GiteaFileChange],
        config: PrRulesConfig,
        result: RulesResult,
    ) -> None:
        reviewers: list[str] = []
        for rule in config.reviewers.values():
            if _matching_files(files, rule.paths):
                reviewers.extend(rule.users)
        result.suggested_reviewers = sorted(set(reviewers))
