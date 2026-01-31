"""Add relationship_stories column to entity_profiles.

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-01-31

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "g7h8i9j0k1l2"
down_revision = "f6g7h8i9j0k1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("entity_profiles", sa.Column("relationship_stories", sa.JSON))


def downgrade() -> None:
    op.drop_column("entity_profiles", "relationship_stories")
