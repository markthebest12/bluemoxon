"""Add fmv_notes and fmv_confidence to eval_runbooks.

Revision ID: o7890123wxyz
Revises: n6789012uvwx
Create Date: 2025-12-16
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "o7890123wxyz"
down_revision = "n6789012uvwx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_runbooks",
        sa.Column("fmv_notes", sa.Text(), nullable=True)
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("fmv_confidence", sa.String(20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("eval_runbooks", "fmv_confidence")
    op.drop_column("eval_runbooks", "fmv_notes")
