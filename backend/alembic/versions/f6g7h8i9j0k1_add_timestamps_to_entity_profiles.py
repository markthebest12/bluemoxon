"""Add created_at and updated_at to entity_profiles (TimestampMixin).

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-01-30

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f6g7h8i9j0k1"
down_revision = "e5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entity_profiles",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "entity_profiles",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Backfill both timestamps from generated_at for existing rows
    op.execute(
        "UPDATE entity_profiles SET created_at = generated_at, updated_at = generated_at"
        " WHERE generated_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("entity_profiles", "updated_at")
    op.drop_column("entity_profiles", "created_at")
