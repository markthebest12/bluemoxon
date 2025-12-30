"""add_source_expired

Add source_expired column to books table for tracking expired source URLs.

Revision ID: v5678901uvwx
Revises: u4567890stuv
Create Date: 2025-12-29 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "v5678901uvwx"
down_revision: str | None = "u4567890stuv"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add source_expired column to books table."""
    op.add_column(
        "books",
        sa.Column("source_expired", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    """Remove source_expired column from books table."""
    op.drop_column("books", "source_expired")
