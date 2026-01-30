"""Add entity_profiles table for caching AI-generated biographical content.

Revision ID: e5f6g7h8i9j0
Revises: z2345678ghij
Create Date: 2026-01-29

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6g7h8i9j0"
down_revision = "z2345678ghij"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_profiles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("bio_summary", sa.Text, nullable=True),
        sa.Column("personal_stories", sa.JSON, nullable=True),
        sa.Column("connection_narratives", sa.JSON, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column(
            "owner_id",
            sa.Integer,
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("entity_type", "entity_id", "owner_id", name="uq_entity_profile"),
    )
    op.create_index(
        "idx_entity_profiles_lookup",
        "entity_profiles",
        ["entity_type", "entity_id", "owner_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_entity_profiles_lookup", table_name="entity_profiles")
    op.drop_table("entity_profiles")
