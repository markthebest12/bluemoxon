"""add_archive_attempts

Add archive_attempts column to books table for retry tracking.

Revision ID: u4567890stuv
Revises: t3456789opqr
Create Date: 2025-12-29 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "u4567890stuv"
down_revision: str | None = "t3456789opqr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add archive_attempts column to books table."""
    op.add_column(
        "books",
        sa.Column("archive_attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Remove archive_attempts column from books table."""
    op.drop_column("books", "archive_attempts")
