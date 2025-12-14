"""add_ship_date_delivery_end

Add ship_date and estimated_delivery_end columns to books table.

Revision ID: k3456789ijkl
Revises: j2345678efgh
Create Date: 2025-12-14 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'k3456789ijkl'
down_revision: str | None = 'j2345678efgh'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ship_date and estimated_delivery_end to books table."""
    op.add_column('books', sa.Column('ship_date', sa.Date(), nullable=True))
    op.add_column('books', sa.Column('estimated_delivery_end', sa.Date(), nullable=True))


def downgrade() -> None:
    """Remove ship_date and estimated_delivery_end from books table."""
    op.drop_column('books', 'estimated_delivery_end')
    op.drop_column('books', 'ship_date')
