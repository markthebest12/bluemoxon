"""add_phone_e164_constraint

Add CHECK constraint for E.164 phone number format and circuit breaker table.

Revision ID: x7890123abcd
Revises: w6789012wxyz
Create Date: 2026-01-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "x7890123abcd"
down_revision: str | None = "w6789012wxyz"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add E.164 constraint and circuit breaker table."""
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT users_phone_number_e164
        CHECK (phone_number IS NULL OR phone_number ~ '^\\+[1-9]\\d{1,14}$')
    """)

    op.execute("""
        CREATE TABLE carrier_circuit_state (
            carrier_name VARCHAR(50) PRIMARY KEY,
            failure_count INTEGER NOT NULL DEFAULT 0,
            last_failure_at TIMESTAMP WITH TIME ZONE,
            circuit_open_until TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    """Remove constraint and table."""
    op.execute("DROP TABLE carrier_circuit_state")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_phone_number_e164")
