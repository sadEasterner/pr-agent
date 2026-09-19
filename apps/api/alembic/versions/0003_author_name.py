"""Store Git host display names for PR authors.

Revision ID: 0003_author_name
Revises: 0002_runtime_controls
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_author_name"
down_revision: str | None = "0002_runtime_controls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pull_requests",
        sa.Column("author_name", sa.String(length=255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("pull_requests", "author_name")
