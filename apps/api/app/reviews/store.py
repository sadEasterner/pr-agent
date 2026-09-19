from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.schemas import AiReviewResult
from app.db.models import Finding, PullRequest, Review, ReviewMetrics
from app.rules.engine import RulesResult
from app.scm.models import PullRequestSnapshot


def _parse_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


class ReviewStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_pull_request(
        self,
        snapshot: PullRequestSnapshot,
        human_review_status: str,
        risk: str,
        recommendation: str,
    ) -> PullRequest:
        result = await self.session.execute(
            select(PullRequest).where(
                PullRequest.repository == snapshot.repository,
                PullRequest.number == snapshot.number,
            )
        )
        pull_request = result.scalar_one_or_none()
        pr_model = snapshot.pull_request
        opened_at = snapshot.opened_at
        closed_at = snapshot.closed_at
        merged_at = snapshot.merged_at
        if pr_model is not None:
            opened_at = opened_at or getattr(pr_model, "created_at", None)
            closed_at = closed_at or getattr(pr_model, "closed_at", None)
            merged_at = merged_at or getattr(pr_model, "merged_at", None)
        status = "merged" if snapshot.merged else snapshot.state
        if pull_request is None:
            pull_request = PullRequest(
                repository=snapshot.repository,
                number=snapshot.number,
                title=snapshot.title,
                author=snapshot.author,
                author_name=snapshot.author_name or snapshot.author,
                description=snapshot.description,
                source_branch=snapshot.source_branch,
                target_branch=snapshot.target_branch,
                gitea_url=snapshot.html_url,
                latest_sha=snapshot.head_sha,
                status=status,
                human_review_status=human_review_status,
                latest_risk=risk,
                latest_recommendation=recommendation,
                opened_at=_parse_dt(opened_at),
                closed_at=_parse_dt(closed_at),
                merged_at=_parse_dt(merged_at),
            )
            self.session.add(pull_request)
        else:
            pull_request.title = snapshot.title
            pull_request.author = snapshot.author
            pull_request.author_name = snapshot.author_name or snapshot.author
            pull_request.description = snapshot.description
            pull_request.source_branch = snapshot.source_branch
            pull_request.target_branch = snapshot.target_branch
            pull_request.gitea_url = snapshot.html_url
            pull_request.latest_sha = snapshot.head_sha
            pull_request.status = status
            pull_request.human_review_status = human_review_status
            pull_request.latest_risk = risk
            pull_request.latest_recommendation = recommendation
            pull_request.closed_at = _parse_dt(closed_at)
            pull_request.merged_at = _parse_dt(merged_at)
        await self.session.flush()
        return pull_request

    async def get_review_for_sha(self, pull_request_id: int, sha: str) -> Review | None:
        result = await self.session.execute(
            select(Review)
            .options(selectinload(Review.findings), selectinload(Review.metrics))
            .where(Review.pull_request_id == pull_request_id, Review.commit_sha == sha)
        )
        return result.scalar_one_or_none()

    async def create_review(
        self,
        pull_request: PullRequest,
        snapshot: PullRequestSnapshot,
        rules_result: RulesResult,
        ai_result: AiReviewResult,
        duration_ms: int,
        ai_model: str | None,
        ai_enabled: bool,
        forced: bool = False,
    ) -> Review:
        review = Review(
            pull_request_id=pull_request.id,
            commit_sha=snapshot.head_sha,
            ai_model=ai_model,
            risk=ai_result.risk.value,
            recommendation=ai_result.recommendation.value,
            summary=ai_result.summary,
            processing_duration_ms=duration_ms,
            rules_result=rules_result.as_dict(),
            ai_enabled=ai_enabled,
            forced=forced,
        )
        self.session.add(review)
        await self.session.flush()
        for finding in ai_result.findings:
            self.session.add(
                Finding(
                    review_id=review.id,
                    severity=finding.severity.value,
                    confidence=finding.confidence,
                    category=finding.category,
                    rule=finding.rule,
                    file_path=finding.file,
                    line=finding.line,
                    message=finding.message,
                    suggested_fix=finding.suggested_fix,
                )
            )
        self.session.add(
            ReviewMetrics(
                review_id=review.id,
                changed_files=rules_result.changed_files,
                lines_added=rules_result.lines_added,
                lines_removed=rules_result.lines_removed,
                test_files_changed=int(rules_result.test_changes),
                number_of_commits=snapshot.commit_count,
            )
        )
        await self.session.flush()
        return review
