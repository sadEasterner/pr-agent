from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin

JSONType = JSON().with_variant(JSONB, "postgresql")


class PullRequest(Base, TimestampMixin):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository", "number", name="uq_pull_requests_repo_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    target_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    gitea_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    latest_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True, nullable=False)
    human_review_status: Mapped[str] = mapped_column(
        String(64), default="pending", index=True, nullable=False
    )
    latest_risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latest_recommendation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviews: Mapped[list[Review]] = relationship(
        back_populates="pull_request",
        cascade="all, delete-orphan",
        order_by="Review.created_at",
    )


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pull_request_id: Mapped[int] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    risk: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    processing_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules_result: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    ai_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    forced: Mapped[bool] = mapped_column(default=False, nullable=False)

    pull_request: Mapped[PullRequest] = relationship(back_populates="reviews")
    findings: Mapped[list[Finding]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="Finding.id",
    )
    metrics: Mapped[ReviewMetrics | None] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    rule: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), default="", index=True, nullable=False)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_fix: Mapped[str] = mapped_column(Text, default="", nullable=False)

    review: Mapped[Review] = relationship(back_populates="findings")


class ReviewMetrics(Base):
    __tablename__ = "review_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    changed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lines_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lines_removed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_files_changed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    number_of_commits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    review: Mapped[Review] = relationship(back_populates="metrics")


class WebhookEvent(Base, TimestampMixin):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "repository",
            "pr_number",
            "event_type",
            "head_sha",
            name="uq_webhook_events_idempotency",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository: Mapped[str] = mapped_column(String(255), nullable=False)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="accepted", nullable=False)
