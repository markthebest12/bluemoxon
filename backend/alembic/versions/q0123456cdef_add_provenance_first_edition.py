"""Add provenance and first edition fields to books.

Add structured, searchable fields for provenance tier tracking and first edition
identification. These fields enable filtering in the UI and AI auto-population
during analysis.

Fields added:
- is_first_edition: Boolean nullable field for first edition status
- has_provenance: Boolean field for provenance presence (default False)
- provenance_tier: String nullable field for provenance tier (Tier 1/2/3)

Revision ID: q0123456cdef
Revises: p8901234yzab
Create Date: 2025-12-19
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "q0123456cdef"
down_revision = "p8901234yzab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add provenance and first edition fields with indexes."""
    # Add is_first_edition column (nullable, no default)
    op.add_column(
        "books",
        sa.Column("is_first_edition", sa.Boolean(), nullable=True)
    )

    # Add has_provenance column (default False, not nullable)
    op.add_column(
        "books",
        sa.Column("has_provenance", sa.Boolean(), nullable=False, server_default=sa.false())
    )

    # Add provenance_tier column (nullable, no default)
    op.add_column(
        "books",
        sa.Column("provenance_tier", sa.String(20), nullable=True)
    )

    # Create indexes for filtering performance
    op.create_index("books_is_first_edition_idx", "books", ["is_first_edition"])
    op.create_index("books_has_provenance_idx", "books", ["has_provenance"])
    op.create_index("books_provenance_tier_idx", "books", ["provenance_tier"])


def downgrade() -> None:
    """Remove provenance and first edition fields and indexes."""
    # Drop indexes first
    op.drop_index("books_provenance_tier_idx", table_name="books")
    op.drop_index("books_has_provenance_idx", table_name="books")
    op.drop_index("books_is_first_edition_idx", table_name="books")

    # Drop columns
    op.drop_column("books", "provenance_tier")
    op.drop_column("books", "has_provenance")
    op.drop_column("books", "is_first_edition")
