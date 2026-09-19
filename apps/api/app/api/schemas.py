from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FindingOut(BaseModel):
    id: int
    severity: str
    confidence: float
    category: str
    rule: str
    file: str
    line: int | None
    message: str
    suggested_fix: str


class MetricsOut(BaseModel):
    changed_files: int
    lines_added: int
    lines_removed: int
    test_files_changed: int
    number_of_commits: int


class ReviewOut(BaseModel):
    id: int
    iteration: int
    commit_sha: str
    created_at: datetime
    ai_model: str | None
    risk: str
    recommendation: str
    summary: str
    processing_duration_ms: int
    findings: list[FindingOut]
    metrics: MetricsOut | None


class PullRequestOut(BaseModel):
    id: int
    repository: str
    number: int
    title: str
    author: str
    author_name: str = ""
    source_branch: str
    target_branch: str
    gitea_url: str
    latest_sha: str
    status: str
    human_review_status: str
    latest_risk: str | None
    latest_recommendation: str | None
    opened_at: datetime | None
    closed_at: datetime | None
    merged_at: datetime | None
    updated_at: datetime
    findings_count: int = 0
    review_iterations: int = 0
    merge_authority: str = "human_approval_required"
    ai_is_not_approval: bool = True


class PullRequestDetailOut(PullRequestOut):
    description: str
    reviews: list[ReviewOut] = Field(default_factory=list)


class SettingsOut(BaseModel):
    automation_mode: str
    allowed_actions: list[str]
    forbidden_actions: list[str]
    ai_enabled: bool
    pr_comments_enabled: bool = True
    ai_provider: str
    ai_model: str
    scm_provider: str = "gitea"
    scm_configured: bool = False
    gitea_configured: bool
    merge_authority: str = "human"
    notes: list[str]


def finding_to_out(finding: Any) -> FindingOut:
    return FindingOut(
        id=finding.id,
        severity=finding.severity,
        confidence=finding.confidence,
        category=finding.category,
        rule=finding.rule,
        file=finding.file_path,
        line=finding.line,
        message=finding.message,
        suggested_fix=finding.suggested_fix,
    )


def review_to_out(review: Any, iteration: int) -> ReviewOut:
    metrics = None
    if review.metrics:
        metrics = MetricsOut(
            changed_files=review.metrics.changed_files,
            lines_added=review.metrics.lines_added,
            lines_removed=review.metrics.lines_removed,
            test_files_changed=review.metrics.test_files_changed,
            number_of_commits=review.metrics.number_of_commits,
        )
    return ReviewOut(
        id=review.id,
        iteration=iteration,
        commit_sha=review.commit_sha,
        created_at=review.created_at,
        ai_model=review.ai_model,
        risk=review.risk,
        recommendation=review.recommendation,
        summary=review.summary,
        processing_duration_ms=review.processing_duration_ms,
        findings=[finding_to_out(item) for item in review.findings],
        metrics=metrics,
    )


def pr_to_out(pull_request: Any) -> PullRequestOut:
    latest = pull_request.reviews[-1] if pull_request.reviews else None
    return PullRequestOut(
        id=pull_request.id,
        repository=pull_request.repository,
        number=pull_request.number,
        title=pull_request.title,
        author=pull_request.author,
        author_name=pull_request.author_name or pull_request.author,
        source_branch=pull_request.source_branch,
        target_branch=pull_request.target_branch,
        gitea_url=pull_request.gitea_url,
        latest_sha=pull_request.latest_sha,
        status=pull_request.status,
        human_review_status=pull_request.human_review_status,
        latest_risk=pull_request.latest_risk,
        latest_recommendation=pull_request.latest_recommendation,
        opened_at=pull_request.opened_at,
        closed_at=pull_request.closed_at,
        merged_at=pull_request.merged_at,
        updated_at=pull_request.updated_at,
        findings_count=len(latest.findings) if latest else 0,
        review_iterations=len(pull_request.reviews),
    )


def pr_to_detail(pull_request: Any) -> PullRequestDetailOut:
    base = pr_to_out(pull_request)
    return PullRequestDetailOut(
        **base.model_dump(),
        description=pull_request.description,
        reviews=[review_to_out(review, index + 1) for index, review in enumerate(pull_request.reviews)],
    )


class PdfMetricIn(BaseModel):
    label: str
    value: str | int | float


class PdfTableIn(BaseModel):
    title: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str | int | float | None]] = Field(default_factory=list)


class PdfReportIn(BaseModel):
    title: str
    subtitle: str | None = None
    metrics: list[PdfMetricIn] = Field(default_factory=list)
    tables: list[PdfTableIn] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
