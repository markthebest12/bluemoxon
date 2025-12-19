"""Add extraction_status to book_analyses.

Tracks whether Stage 2 structured data extraction succeeded or fell back to YAML
parsing. This enables UI indicators when extraction quality is degraded.

Values:
- "success": Stage 2 extraction worked properly
- "degraded": Fell back to YAML parsing (e.g., Bedrock throttling)
- "failed": Extraction error, no structured data available
- null: Legacy/unknown (pre-existing analyses)

Revision ID: r1234567ghij
Revises: q0123456cdef
Create Date: 2025-12-19
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "r1234567ghij"
down_revision = "q0123456cdef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add extraction_status column to book_analyses."""
    op.add_column(
        "book_analyses",
        sa.Column("extraction_status", sa.String(20), nullable=True)
    )


def downgrade() -> None:
    """Remove extraction_status column."""
    op.drop_column("book_analyses", "extraction_status")
