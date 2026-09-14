from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import Finding, PullRequest, Review, ReviewMetrics


def _apply_filters(stmt: Any, filters: list[Any]) -> Any:
    return stmt.where(*filters) if filters else stmt


def _since(days: int | None) -> datetime | None:
    if not days:
        return None
    return datetime.now(UTC) - timedelta(days=days)


def _duration_seconds(session: AsyncSession, end: Any, start: Any) -> ColumnElement[Any]:
    bind = session.bind or session.get_bind()
    dialect = bind.dialect.name if bind is not None else "postgresql"
    if dialect == "sqlite":
        return func.julianday(end) * 86400.0 - func.julianday(start) * 86400.0
    return func.extract("epoch", end) - func.extract("epoch", start)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _pr_filters(
        self,
        repository: str | None = None,
        author: str | None = None,
        days: int | None = None,
    ) -> list[Any]:
        filters: list[Any] = []
        if repository:
            filters.append(PullRequest.repository == repository)
        if author:
            filters.append(PullRequest.author == author)
        since = _since(days)
        if since is not None:
            filters.append(PullRequest.created_at >= since)
        return filters

    async def summary(
        self,
        repository: str | None = None,
        author: str | None = None,
        days: int | None = None,
    ) -> dict[str, Any]:
        filters = self._pr_filters(repository, author, days)
        stmt_count = select(func.count()).select_from(PullRequest)
        if filters:
            stmt_count = stmt_count.where(*filters)
        reviewed = await self.session.scalar(stmt_count)
        waiting = await self.session.scalar(
            select(func.count())
            .select_from(PullRequest)
            .where(PullRequest.human_review_status == "waiting_for_human", *filters)
        )
        high_risk = await self.session.scalar(
            select(func.count())
            .select_from(PullRequest)
            .where(PullRequest.latest_risk.in_(["high", "critical"]), *filters)
        )
        merged = await self.session.scalar(
            select(func.count())
            .select_from(PullRequest)
            .where(PullRequest.status == "merged", *filters)
        )
        size_row = await self.session.execute(
            select(
                func.avg(ReviewMetrics.lines_added + ReviewMetrics.lines_removed),
                func.avg(ReviewMetrics.changed_files),
            )
        )
        avg_lines, avg_files = size_row.one()
        merge_times = await self.session.scalar(
            select(
                func.avg(_duration_seconds(self.session, PullRequest.merged_at, PullRequest.opened_at))
            ).where(
                PullRequest.merged_at.is_not(None),
                PullRequest.opened_at.is_not(None),
                *filters,
            )
        )
        first_review = await self.session.scalar(
            select(
                func.avg(_duration_seconds(self.session, Review.created_at, PullRequest.opened_at))
            )
            .select_from(Review)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .where(PullRequest.opened_at.is_not(None), *filters)
        )
        week_ago = datetime.now(UTC) - timedelta(days=7)
        findings_week = await self.session.scalar(
            select(func.count()).select_from(Finding).where(Finding.created_at >= week_ago)
        )
        return {
            "prs_reviewed": int(reviewed or 0),
            "prs_waiting_for_human_review": int(waiting or 0),
            "high_risk_prs": int(high_risk or 0),
            "prs_merged": int(merged or 0),
            "average_pr_size_lines": float(avg_lines or 0),
            "average_pr_size_files": float(avg_files or 0),
            "average_merge_time_seconds": float(merge_times or 0),
            "average_time_to_first_review_seconds": float(first_review or 0),
            "findings_this_week": int(findings_week or 0),
        }

    async def trends(self, days: int = 30) -> dict[str, Any]:
        since = _since(days) or _since(30)
        reviews = await self.session.execute(
            select(func.date(Review.created_at), func.count())
            .where(Review.created_at >= since)
            .group_by(func.date(Review.created_at))
            .order_by(func.date(Review.created_at))
        )
        risk = await self.session.execute(select(Review.risk, func.count()).group_by(Review.risk))
        sizes = await self.session.execute(
            select(
                func.date(Review.created_at),
                func.avg(ReviewMetrics.lines_added + ReviewMetrics.lines_removed),
            )
            .join(ReviewMetrics, ReviewMetrics.review_id == Review.id)
            .where(Review.created_at >= since)
            .group_by(func.date(Review.created_at))
            .order_by(func.date(Review.created_at))
        )
        merges = await self.session.execute(
            select(
                func.date(PullRequest.merged_at),
                func.avg(
                    _duration_seconds(self.session, PullRequest.merged_at, PullRequest.opened_at)
                ),
            )
            .where(PullRequest.merged_at.is_not(None), PullRequest.opened_at.is_not(None))
            .group_by(func.date(PullRequest.merged_at))
            .order_by(func.date(PullRequest.merged_at))
        )
        return {
            "reviews_over_time": [
                {"date": str(day), "count": count} for day, count in reviews.all()
            ],
            "risk_distribution": [
                {"risk": risk_name, "count": count} for risk_name, count in risk.all()
            ],
            "pr_size_trend": [
                {"date": str(day), "average_lines": float(avg or 0)} for day, avg in sizes.all()
            ],
            "merge_time_trend": [
                {"date": str(day), "average_seconds": float(avg or 0)}
                for day, avg in merges.all()
            ],
        }

    async def findings(self, days: int | None = None) -> dict[str, Any]:
        filters: list[Any] = []
        since = _since(days)
        if since is not None:
            filters.append(Finding.created_at >= since)
        severity = await self.session.execute(
            _apply_filters(select(Finding.severity, func.count()), filters).group_by(Finding.severity)
        )
        category = await self.session.execute(
            _apply_filters(select(Finding.category, func.count()), filters).group_by(Finding.category)
        )
        rules = await self.session.execute(
            _apply_filters(select(Finding.rule, func.count()), filters)
            .group_by(Finding.rule)
            .order_by(func.count().desc())
            .limit(20)
        )
        modules = await self.session.execute(
            _apply_filters(select(Finding.file_path, func.count()), filters)
            .group_by(Finding.file_path)
            .order_by(func.count().desc())
            .limit(20)
        )
        over_time = await self.session.execute(
            _apply_filters(
                select(func.date(Finding.created_at), Finding.severity, func.count()),
                filters,
            )
            .group_by(func.date(Finding.created_at), Finding.severity)
            .order_by(func.date(Finding.created_at))
        )
        return {
            "by_severity": [{"severity": name, "count": count} for name, count in severity.all()],
            "by_category": [{"category": name, "count": count} for name, count in category.all()],
            "common_violated_rules": [
                {"rule": name or "unspecified", "count": count} for name, count in rules.all()
            ],
            "recurring_modules": [
                {"path": path or "unknown", "count": count} for path, count in modules.all()
            ],
            "over_time": [
                {"date": str(day), "severity": sev, "count": count}
                for day, sev, count in over_time.all()
            ],
        }

    async def repositories(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(
                PullRequest.repository,
                func.count(func.distinct(PullRequest.id)),
                func.count(Review.id),
            )
            .outerjoin(Review, Review.pull_request_id == PullRequest.id)
            .group_by(PullRequest.repository)
        )
        items: list[dict[str, Any]] = []
        for repository, prs, reviews in result.all():
            merged = await self.session.scalar(
                select(func.count()).where(
                    PullRequest.repository == repository,
                    PullRequest.status == "merged",
                )
            )
            high_risk = await self.session.scalar(
                select(func.count()).where(
                    PullRequest.repository == repository,
                    PullRequest.latest_risk.in_(["high", "critical"]),
                )
            )
            items.append(
                {
                    "repository": repository,
                    "prs": int(prs or 0),
                    "reviews": int(reviews or 0),
                    "merged": int(merged or 0),
                    "high_risk": int(high_risk or 0),
                }
            )
        return items

    def _list_query(
        self,
        repository: str | None = None,
        risk: str | None = None,
        status: str | None = None,
        author: str | None = None,
    ) -> Select[tuple[PullRequest]]:
        stmt = select(PullRequest).options(
            selectinload(PullRequest.reviews).selectinload(Review.findings),
            selectinload(PullRequest.reviews).selectinload(Review.metrics),
        )
        filters: list[Any] = []
        if repository:
            filters.append(PullRequest.repository == repository)
        if risk:
            filters.append(PullRequest.latest_risk == risk)
        if status:
            filters.append(PullRequest.human_review_status == status)
        if author:
            filters.append(PullRequest.author == author)
        if filters:
            stmt = stmt.where(and_(*filters))
        return stmt.order_by(PullRequest.updated_at.desc())

    async def list_prs(
        self,
        repository: str | None = None,
        risk: str | None = None,
        status: str | None = None,
        author: str | None = None,
        severity: str | None = None,
    ) -> list[PullRequest]:
        result = await self.session.execute(self._list_query(repository, risk, status, author))
        pull_requests = list(result.scalars().unique().all())
        if not severity:
            return pull_requests
        filtered: list[PullRequest] = []
        for pull_request in pull_requests:
            latest = pull_request.reviews[-1] if pull_request.reviews else None
            if latest and any(finding.severity == severity for finding in latest.findings):
                filtered.append(pull_request)
        return filtered

    async def get_pr(self, repository: str, number: int) -> PullRequest | None:
        result = await self.session.execute(
            select(PullRequest)
            .options(
                selectinload(PullRequest.reviews).selectinload(Review.findings),
                selectinload(PullRequest.reviews).selectinload(Review.metrics),
            )
            .where(PullRequest.repository == repository, PullRequest.number == number)
        )
        return result.scalar_one_or_none()
