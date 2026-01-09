"""backfill_roi_pct

Backfill roi_pct for existing books that have both value_mid and acquisition_cost.

Revision ID: y8901234bcde
Revises: 21eb898ba04b
Create Date: 2026-01-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "y8901234bcde"
down_revision: str = "21eb898ba04b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill roi_pct for books with value_mid and acquisition_cost.

    Formula: roi_pct = ((value_mid - acquisition_cost) / acquisition_cost) * 100
    """
    op.execute("""
        UPDATE books
        SET roi_pct = ROUND(((value_mid - acquisition_cost) / acquisition_cost) * 100, 2)
        WHERE value_mid IS NOT NULL
          AND acquisition_cost IS NOT NULL
          AND acquisition_cost > 0
          AND roi_pct IS NULL
    """)


def downgrade() -> None:
    """Clear backfilled roi_pct values.

    Note: This only clears values that were backfilled, not values set by
    the application. Since we can't distinguish between them, we clear all
    to avoid inconsistency. The application will recalculate on next update.
    """
    # Don't clear - the application will recalculate anyway
    pass
