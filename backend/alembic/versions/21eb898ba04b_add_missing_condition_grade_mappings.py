"""add_missing_condition_grade_mappings

Revision ID: 21eb898ba04b
Revises: dd7f743834bc
Create Date: 2026-01-08

Adds missing condition_grade mappings not covered in dd7f743834bc:
- G+ → GOOD
- G- → FAIR
- NF- → VERY_GOOD
- F- → NEAR_FINE
- Good- → FAIR
- VGC (Very Good Condition) → VERY_GOOD
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21eb898ba04b"
down_revision: str | None = "dd7f743834bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing condition_grade mappings.
    # Idempotent - only updates rows not already normalized.
    op.execute("""
        UPDATE books
        SET condition_grade = CASE LOWER(TRIM(condition_grade))
            -- G variants
            WHEN 'g+' THEN 'GOOD'
            WHEN 'g +' THEN 'GOOD'
            WHEN 'g-' THEN 'FAIR'
            WHEN 'g -' THEN 'FAIR'
            -- Good- variants
            WHEN 'good-' THEN 'FAIR'
            WHEN 'good -' THEN 'FAIR'
            -- NF variants
            WHEN 'nf-' THEN 'VERY_GOOD'
            WHEN 'nf -' THEN 'VERY_GOOD'
            WHEN 'nf+' THEN 'FINE'
            WHEN 'nf +' THEN 'FINE'
            -- F variants
            WHEN 'f-' THEN 'NEAR_FINE'
            WHEN 'f -' THEN 'NEAR_FINE'
            WHEN 'f+' THEN 'FINE'
            WHEN 'f +' THEN 'FINE'
            -- VGC (Very Good Condition)
            WHEN 'vgc' THEN 'VERY_GOOD'
            WHEN 'gc' THEN 'GOOD'
            WHEN 'fc' THEN 'FAIR'
            ELSE condition_grade
        END
        WHERE condition_grade IS NOT NULL
        AND UPPER(condition_grade) NOT IN ('FINE', 'NEAR_FINE', 'VERY_GOOD', 'GOOD', 'FAIR', 'POOR')
    """)


def downgrade() -> None:
    # NO-OP: Data normalization cannot be reversed
    pass
