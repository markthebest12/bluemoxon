"""Narrow entity_profile unique constraint to (entity_type, entity_id).

Revision ID: 184855af397c
Revises: z3456789ijkl
Create Date: 2026-02-03

Issue #1731: The EntityProfile unique constraint previously included owner_id,
but profiles are per-entity not per-user (fixed in #1715). This migration
narrows the constraint to (entity_type, entity_id) only. The owner_id column
is retained because it is still referenced in service and worker code.

Before changing the constraint, duplicate rows (same entity_type + entity_id
but different owner_id) are deduplicated by keeping the most recently updated
profile.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "184855af397c"
down_revision: str | None = "z3456789ijkl"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Deduplicate profiles and narrow unique constraint."""
    # Deduplicate: keep most recently updated profile per (entity_type, entity_id)
    op.execute(
        """
        DELETE FROM entity_profiles
        WHERE id NOT IN (
            SELECT DISTINCT ON (entity_type, entity_id) id
            FROM entity_profiles
            ORDER BY entity_type, entity_id, updated_at DESC NULLS LAST
        )
        """
    )
    # Drop old constraint that included owner_id
    op.drop_constraint("uq_entity_profile", "entity_profiles", type_="unique")
    # Add new constraint on (entity_type, entity_id) only
    op.create_unique_constraint(
        "uq_entity_profile", "entity_profiles", ["entity_type", "entity_id"]
    )


def downgrade() -> None:
    """Restore original constraint including owner_id."""
    op.drop_constraint("uq_entity_profile", "entity_profiles", type_="unique")
    op.create_unique_constraint(
        "uq_entity_profile",
        "entity_profiles",
        ["entity_type", "entity_id", "owner_id"],
    )
