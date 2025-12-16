"""add_acquisition_cost

Add acquisition_cost column to books table.
This represents the total cost paid including shipping and tax,
separate from purchase_price which is just the listing price.

Revision ID: l4567890mnop
Revises: k3456789ijkl
Create Date: 2025-12-15 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'l4567890mnop'
down_revision: str | None = 'k3456789ijkl'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add acquisition_cost to books table."""
    op.add_column('books', sa.Column('acquisition_cost', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    """Remove acquisition_cost from books table."""
    op.drop_column('books', 'acquisition_cost')
