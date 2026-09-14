from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class LabelRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paths: list[str] = Field(default_factory=list)


class ReviewerRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paths: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)


class PrRulesConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    require_description: bool = True
    min_description_length: int = 20
    max_changed_lines: int = 500
    max_changed_files: int = 40
    dangerous_paths: list[str] = Field(default_factory=list)
    migration_paths: list[str] = Field(default_factory=list)
    infrastructure_paths: list[str] = Field(default_factory=list)
    test_paths: list[str] = Field(default_factory=list)
    enforce_workspace_isolation: bool = True
    labels: dict[str, LabelRule] = Field(default_factory=dict)
    reviewers: dict[str, ReviewerRule] = Field(default_factory=dict)


class AiReviewConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    minimum_confidence: float = 0.75
    check: list[str] = Field(default_factory=list)
    ignore: list[str] = Field(default_factory=list)


class PathRuleConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check: list[str] = Field(default_factory=list)
    ignore: list[str] = Field(default_factory=list)


class AutomationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: str = "review_only"
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)


class ReviewRulesConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pr_rules: PrRulesConfig = Field(default_factory=PrRulesConfig)
    ai_review: AiReviewConfig = Field(default_factory=AiReviewConfig)
    path_rules: dict[str, PathRuleConfig] = Field(default_factory=dict)
    project_rules: list[str] = Field(default_factory=list)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)


class RepositoryRulesConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_rules: list[str] = Field(default_factory=list)
    path_rules: dict[str, PathRuleConfig] = Field(default_factory=dict)
    ai_review: AiReviewConfig | None = None


@dataclass
class LoadedRules:
    global_rules: ReviewRulesConfig
    repository_rules: dict[str, RepositoryRulesConfig] = field(default_factory=dict)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML at {path} must be a mapping")
    return payload


def load_review_rules(config_dir: Path) -> LoadedRules:
    global_path = config_dir / "review-rules.yaml"
    global_rules = ReviewRulesConfig.model_validate(_load_yaml(global_path))
    repository_rules: dict[str, RepositoryRulesConfig] = {}
    repo_dir = config_dir / "repositories"
    if repo_dir.exists():
        for file_path in repo_dir.glob("*.yaml"):
            if file_path.name.lower() == "readme.yaml":
                continue
            key = file_path.stem.replace("__", "/")
            repository_rules[key] = RepositoryRulesConfig.model_validate(_load_yaml(file_path))
    return LoadedRules(global_rules=global_rules, repository_rules=repository_rules)
