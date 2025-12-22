"""add_author_tier

Add tier column to authors table for scoring calculations.

Revision ID: s2345678klmn
Revises: 6e90a0c87832
Create Date: 2025-12-21 19:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 's2345678klmn'
down_revision: str | None = '6e90a0c87832'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add tier column to authors table."""
    # Add tier column
    op.add_column('authors', sa.Column('tier', sa.String(10), nullable=True))


def downgrade() -> None:
    """Remove tier column from authors table."""
    op.drop_column('authors', 'tier')
