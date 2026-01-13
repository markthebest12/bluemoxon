"""Add founded_year and closed_year to binders table.

Revision ID: b2c3d4e5f6a7
Revises: a1f2e3d4c5b6
Create Date: 2026-01-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1f2e3d4c5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("binders", sa.Column("founded_year", sa.Integer(), nullable=True))
    op.add_column("binders", sa.Column("closed_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("binders", "closed_year")
    op.drop_column("binders", "founded_year")
