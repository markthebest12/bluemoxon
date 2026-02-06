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
    # Uses canonical ordering (lower node ID string first) and ON CONFLICT
    # to handle duplicates from A→B and B→A stored in separate profiles.
    op.execute(
        """
        INSERT INTO ai_connections (
            source_type, source_id, target_type, target_id,
            relationship, sub_type, confidence, evidence
        )
        SELECT
            -- Canonical ordering: lower node string first
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (conn->>'target_type' || ':' || conn->>'target_id')
                 THEN ep.entity_type
                 ELSE conn->>'target_type'
            END AS source_type,
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (conn->>'target_type' || ':' || conn->>'target_id')
                 THEN ep.entity_id
                 ELSE CAST(conn->>'target_id' AS INTEGER)
            END AS source_id,
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (conn->>'target_type' || ':' || conn->>'target_id')
                 THEN conn->>'target_type'
                 ELSE ep.entity_type
            END AS target_type,
            CASE WHEN (ep.entity_type || ':' || CAST(ep.entity_id AS TEXT))
                      <= (conn->>'target_type' || ':' || conn->>'target_id')
                 THEN CAST(conn->>'target_id' AS INTEGER)
                 ELSE ep.entity_id
            END AS target_id,
            conn->>'relationship',
            conn->>'sub_type',
            COALESCE(CAST(conn->>'confidence' AS FLOAT), 0.5),
            conn->>'evidence'
        FROM entity_profiles ep,
             json_array_elements(ep.ai_connections) AS conn
        WHERE ep.ai_connections IS NOT NULL
          AND json_array_length(ep.ai_connections) > 0
          AND conn->>'relationship' IS NOT NULL
          AND conn->>'target_type' IS NOT NULL
          AND conn->>'target_id' IS NOT NULL
        ON CONFLICT (source_type, source_id, target_type, target_id, relationship)
        DO UPDATE SET
            confidence = GREATEST(ai_connections.confidence, EXCLUDED.confidence),
            evidence = COALESCE(EXCLUDED.evidence, ai_connections.evidence),
            sub_type = COALESCE(EXCLUDED.sub_type, ai_connections.sub_type),
            updated_at = now()
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
