"""backfill_tracking_active_for_in_transit_books

Data migration to activate tracking for existing in-transit books.

The carrier API support migration (w6789012wxyz) added the tracking_active
column but didn't backfill existing books. This migration sets tracking_active
to true for books that:
- Have a tracking number
- Are currently IN_TRANSIT status
- Don't already have tracking_active set

This ensures existing shipments are picked up by the hourly polling job.

Revision ID: d3b3c3c4dd80
Revises: x7890123abcd
Create Date: 2026-01-03 09:16:27.024618

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3b3c3c4dd80"
down_revision: str | None = "x7890123abcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Activate tracking for existing in-transit books with tracking numbers."""
    op.execute(
        sa.text(
            """
            UPDATE books
            SET tracking_active = true
            WHERE tracking_number IS NOT NULL
              AND status = 'IN_TRANSIT'
              AND tracking_active = false
            """
        )
    )


def downgrade() -> None:
    """No rollback - this was a bug fix for missing data."""
    pass
