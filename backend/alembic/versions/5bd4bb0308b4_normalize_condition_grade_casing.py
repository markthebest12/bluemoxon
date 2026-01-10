"""normalize_condition_grade_casing

Revision ID: 5bd4bb0308b4
Revises: y8901234bcde
Create Date: 2026-01-09 19:59:29.788558

Normalizes condition_grade values to UPPERCASE. The enum already enforces
SCREAMING_CASE for new data, but legacy data may have inconsistent casing
(e.g., "Good" vs "GOOD", "Fair" vs "FAIR").

Closes #1006
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5bd4bb0308b4"
down_revision: str | None = "y8901234bcde"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Normalize condition_grade to UPPERCASE."""
    op.execute("""
        UPDATE books
        SET condition_grade = UPPER(condition_grade)
        WHERE condition_grade IS NOT NULL
          AND condition_grade != UPPER(condition_grade)
    """)


def downgrade() -> None:
    """No downgrade - data normalization is one-way."""
    pass
