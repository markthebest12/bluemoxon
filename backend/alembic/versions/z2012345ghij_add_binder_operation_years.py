"""Add founded_year and closed_year to binders table.

Revision ID: z2012345ghij
Revises: z1012345efgh
Create Date: 2026-01-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "z2012345ghij"
down_revision = "z1012345efgh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("binders", sa.Column("founded_year", sa.Integer(), nullable=True))
    op.add_column("binders", sa.Column("closed_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("binders", "closed_year")
    op.drop_column("binders", "founded_year")
