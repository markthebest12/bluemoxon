"""add_tracking_fields

Add tracking_number, tracking_carrier, and tracking_url columns
to books table for shipment tracking.

Revision ID: j2345678efgh
Revises: i0123456abcd
Create Date: 2025-12-13 17:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'j2345678efgh'
down_revision: str | None = 'i0123456abcd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add tracking fields to books table."""
    op.add_column('books', sa.Column('tracking_number', sa.String(100), nullable=True))
    op.add_column('books', sa.Column('tracking_carrier', sa.String(50), nullable=True))
    op.add_column('books', sa.Column('tracking_url', sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove tracking fields from books table."""
    op.drop_column('books', 'tracking_url')
    op.drop_column('books', 'tracking_carrier')
    op.drop_column('books', 'tracking_number')
