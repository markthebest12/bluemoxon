"""add_is_complete_field

Add is_complete boolean field to books table to properly track
whether multi-volume sets are complete (all volumes present).

Revision ID: h8901234efgh
Revises: g7890123def0
Create Date: 2025-12-11 11:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8901234efgh'
down_revision: str | None = 'g7890123def0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_complete column to books table."""
    # Add column with default True (assume sets are complete unless marked otherwise)
    op.add_column(
        'books',
        sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    """Remove is_complete column."""
    op.drop_column('books', 'is_complete')
