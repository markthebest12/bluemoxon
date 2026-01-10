"""normalize_condition_grade_casing

Revision ID: 5bd4bb0308b4
Revises: y8901234bcde
Create Date: 2026-01-09 19:59:29.788558

Normalizes condition_grade values to UPPERCASE. The enum already enforces
SCREAMING_CASE for new data, but legacy data may have inconsistent casing
(e.g., "Good" vs "GOOD", "Fair" vs "FAIR").

Closes #1006
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5bd4bb0308b4"
down_revision: str | None = "y8901234bcde"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Normalize condition_grade to UPPERCASE with batching and backup."""
    # First, backup original values to a temp column
    op.add_column(
        "books", sa.Column("_condition_grade_backup", sa.String(20), nullable=True)
    )
    op.execute("""
        UPDATE books
        SET _condition_grade_backup = condition_grade
        WHERE condition_grade IS NOT NULL
    """)

    # Update all rows in a single statement
    # Note: For small tables (<10k rows), single UPDATE is efficient
    # For larger tables, consider using migration_sql.py HTTP endpoint
    # which can run multiple statements with commits between them
    op.execute("""
        UPDATE books
        SET condition_grade = UPPER(condition_grade)
        WHERE condition_grade IS NOT NULL
          AND condition_grade != UPPER(condition_grade)
    """)


def downgrade() -> None:
    """Restore original condition_grade values from backup."""
    op.execute("""
        UPDATE books
        SET condition_grade = _condition_grade_backup
        WHERE _condition_grade_backup IS NOT NULL
    """)
    op.drop_column("books", "_condition_grade_backup")
