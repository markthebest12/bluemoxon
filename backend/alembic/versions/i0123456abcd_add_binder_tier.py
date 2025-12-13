"""add_binder_tier

Add tier column to binders table for scoring calculations.
Tier 1 binders (Zaehnsdorf, Rivière, etc.) get +40 points,
Tier 2 binders get +20 points.

Revision ID: i0123456abcd
Revises: a1234567bcde
Create Date: 2025-12-13 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'i0123456abcd'
down_revision: str | None = 'a1234567bcde'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add tier column to binders table and populate known tiers."""
    # Add tier column
    op.add_column('binders', sa.Column('tier', sa.String(20), nullable=True))

    # Populate Tier 1 binders (per Victorian Book Acquisition Guide)
    op.execute("""
        UPDATE binders SET tier = 'TIER_1'
        WHERE name IN ('Zaehnsdorf', 'Rivière', 'Riviere', 'Sangorski',
                       'Bayntun', 'Bayntun-Riviere', 'Hayday')
    """)

    # Populate Tier 2 binders
    op.execute("""
        UPDATE binders SET tier = 'TIER_2'
        WHERE name IN ('Bumpus', 'Sotheran', 'Root & Son', 'Morrell')
    """)


def downgrade() -> None:
    """Remove tier column from binders table."""
    op.drop_column('binders', 'tier')
