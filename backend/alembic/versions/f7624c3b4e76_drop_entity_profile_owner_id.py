"""Drop owner_id column from entity_profiles.

Revision ID: f7624c3b4e76
Revises: 184855af397c
Create Date: 2026-02-04

Issue #1765: The owner_id column on entity_profiles is vestigial after
narrowing the unique constraint in #1731. Profiles are per-entity, not
per-user. The column and its foreign key are removed here.

Note: ProfileGenerationJob.owner_id is intentionally preserved — it
provides a legitimate audit trail for batch generation jobs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7624c3b4e76"
down_revision: str | None = "184855af397c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop owner_id column from entity_profiles."""
    op.drop_column("entity_profiles", "owner_id")


def downgrade() -> None:
    """Re-add owner_id column (nullable, since existing rows won't have it)."""
    op.add_column(
        "entity_profiles",
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
