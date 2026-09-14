"""Create PR review history schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository", sa.String(length=255), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_branch", sa.String(length=255), nullable=False),
        sa.Column("target_branch", sa.String(length=255), nullable=False),
        sa.Column("gitea_url", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("latest_sha", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("human_review_status", sa.String(length=64), nullable=False, server_default="pending"),
        sa.Column("latest_risk", sa.String(length=32), nullable=True),
        sa.Column("latest_recommendation", sa.String(length=64), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repository", "number", name="uq_pull_requests_repo_number"),
    )
    op.create_index("ix_pull_requests_repository", "pull_requests", ["repository"])
    op.create_index("ix_pull_requests_author", "pull_requests", ["author"])
    op.create_index("ix_pull_requests_latest_sha", "pull_requests", ["latest_sha"])
    op.create_index("ix_pull_requests_status", "pull_requests", ["status"])
    op.create_index("ix_pull_requests_human_review_status", "pull_requests", ["human_review_status"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pull_request_id",
            sa.Integer(),
            sa.ForeignKey("pull_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("ai_model", sa.String(length=128), nullable=True),
        sa.Column("risk", sa.String(length=32), nullable=False),
        sa.Column("recommendation", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("processing_duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rules_result", sa.JSON(), nullable=False),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("forced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reviews_pull_request_id", "reviews", ["pull_request_id"])
    op.create_index("ix_reviews_commit_sha", "reviews", ["commit_sha"])
    op.create_index("ix_reviews_risk", "reviews", ["risk"])
    op.create_index("ix_reviews_recommendation", "reviews", ["recommendation"])

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("rule", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("file_path", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggested_fix", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_findings_review_id", "findings", ["review_id"])
    op.create_index("ix_findings_severity", "findings", ["severity"])
    op.create_index("ix_findings_category", "findings", ["category"])
    op.create_index("ix_findings_file_path", "findings", ["file_path"])

    op.create_table(
        "review_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("changed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lines_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lines_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("test_files_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("number_of_commits", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("review_id", name="uq_review_metrics_review_id"),
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository", sa.String(length=255), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("head_sha", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="accepted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "repository",
            "pr_number",
            "event_type",
            "head_sha",
            name="uq_webhook_events_idempotency",
        ),
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("review_metrics")
    op.drop_table("findings")
    op.drop_table("reviews")
    op.drop_table("pull_requests")
