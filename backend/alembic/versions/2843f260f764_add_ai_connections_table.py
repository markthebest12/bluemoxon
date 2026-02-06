"""Add ai_connections table.

Revision ID: 2843f260f764
Revises: e9a5101c8557
Create Date: 2026-02-05

Issue #1813: Canonical relational table for AI-discovered personal
connections.  Replaces per-entity JSON storage in entity_profiles.ai_connections.
Includes data migration from existing JSON to the new table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2843f260f764"
down_revision: str | None = "e9a5101c8557"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ai_connections table and migrate data from JSON column."""
    op.create_table(
        "ai_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("relationship", sa.String(20), nullable=False),
        sa.Column("sub_type", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "relationship",
            name="uq_ai_connection",
        ),
    )
    op.create_index(
        "ix_ai_connections_source", "ai_connections", ["source_type", "source_id"]
    )
    op.create_index(
        "ix_ai_connections_target", "ai_connections", ["target_type", "target_id"]
    )

    # Data migration: copy existing JSON ai_connections into the new table.
    # Uses DISTINCT ON to deduplicate A→B / B→A pairs that resolve to the
    # same canonical key, keeping the row with the highest confidence.
    op.execute(
        """
        INSERT INTO ai_connections (
            source_type, source_id, target_type, target_id,
            relationship, sub_type, confidence, evidence
        )
        SELECT DISTINCT ON (source_type, source_id, target_type, target_id, relationship)
            source_type, source_id, target_type, target_id,
            relationship, sub_type, confidence, evidence
        FROM (
            SELECT
                CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                          <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                     THEN ep.entity_type
                     ELSE c.target_type
                END AS source_type,
                CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                          <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                     THEN ep.entity_id
                     ELSE c.target_id
                END AS source_id,
                CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                          <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                     THEN c.target_type
                     ELSE ep.entity_type
                END AS target_type,
                CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                          <= (c.target_type || ':' || CAST(c.target_id AS TEXT))
                     THEN c.target_id
                     ELSE ep.entity_id
                END AS target_id,
                c.relationship,
                c.sub_type,
                COALESCE(c.confidence, 0.5) AS confidence,
                c.evidence
            FROM entity_profiles ep,
                 jsonb_to_recordset(ep.ai_connections::jsonb) AS c(
                     target_type text,
                     target_id integer,
                     relationship text,
                     sub_type text,
                     confidence float,
                     evidence text
                 )
            WHERE ep.ai_connections IS NOT NULL
              AND c.relationship IS NOT NULL
              AND c.target_type IS NOT NULL
              AND c.target_id IS NOT NULL
        ) AS raw
        ORDER BY source_type, source_id, target_type, target_id, relationship,
                 confidence DESC
        ON CONFLICT (source_type, source_id, target_type, target_id, relationship)
        DO NOTHING
        """
    )


def downgrade() -> None:
    """Drop ai_connections table.

    NOTE: This is a one-way data migration. Connections created after upgrade
    are stored only in the table, not in entity_profiles.ai_connections JSON.
    Rolling back will lose post-migration AI connection data.
    """
    op.drop_index("ix_ai_connections_target", table_name="ai_connections")
    op.drop_index("ix_ai_connections_source", table_name="ai_connections")
    op.drop_table("ai_connections")
