"""Consolidate admin_config into app_config table.

Revision ID: z4567890klmn
Revises: z3456789ijkl, 708c5a15f5bb
Create Date: 2026-02-04

Issue #1776: Merge admin_config rows into app_config and drop admin_config table.
Also merges the two migration heads (z3456789ijkl and 708c5a15f5bb).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "z4567890klmn"
down_revision: tuple[str, ...] = ("z3456789ijkl", "708c5a15f5bb")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # admin_config.value is JSON (e.g. 1.28 as JSON number).
    # app_config.value is String(500). Cast via JSON text representation,
    # then strip surrounding double-quotes if the DB wraps them.
    op.execute("""
        INSERT INTO app_config (key, value, description, updated_at)
        SELECT key,
               TRIM(BOTH '"' FROM value::text),
               'Migrated from admin_config',
               updated_at
        FROM admin_config
        ON CONFLICT (key) DO NOTHING
    """)
    op.drop_table("admin_config")


def downgrade() -> None:
    # Recreate with JSONB to match the original migration (9d7720474d6d)
    op.create_table(
        "admin_config",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    # Move rate rows back as JSON numbers.
    # Note: only these two keys existed in admin_config at migration time.
    # Any new rate keys added post-migration won't be moved back.
    op.execute("""
        INSERT INTO admin_config (key, value)
        SELECT key, value::jsonb
        FROM app_config
        WHERE key IN ('gbp_to_usd_rate', 'eur_to_usd_rate')
    """)
    op.execute("""
        DELETE FROM app_config
        WHERE key IN ('gbp_to_usd_rate', 'eur_to_usd_rate')
    """)
