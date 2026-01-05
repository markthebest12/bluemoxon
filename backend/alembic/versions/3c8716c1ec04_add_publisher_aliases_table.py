"""add_publisher_aliases_table

Revision ID: 3c8716c1ec04
Revises: 7a6d67bc123e
Create Date: 2026-01-04 22:27:10.951969

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c8716c1ec04"
down_revision: str | None = "7a6d67bc123e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Seed data: (canonical_name, tier, [aliases])
PUBLISHER_SEEDS = [
    # Tier 1 - Major Victorian/Edwardian publishers
    ("Macmillan and Co.", "TIER_1", ["Macmillan"]),
    ("Chapman & Hall", "TIER_1", ["Chapman and Hall"]),
    ("Smith, Elder & Co.", "TIER_1", ["Smith Elder"]),
    ("John Murray", "TIER_1", ["Murray"]),
    ("William Blackwood and Sons", "TIER_1", ["Blackwood"]),
    ("Edward Moxon and Co.", "TIER_1", ["Moxon"]),
    ("Oxford University Press", "TIER_1", ["OUP"]),
    ("Clarendon Press", "TIER_1", []),
    ("Longmans, Green & Co.", "TIER_1", ["Longmans", "Longman"]),
    ("Harper & Brothers", "TIER_1", ["Harper"]),
    ("D. Appleton and Company", "TIER_1", ["Appleton"]),
    ("Little, Brown, and Company", "TIER_1", ["Little Brown"]),
    ("Richard Bentley", "TIER_1", ["Bentley"]),
    # Tier 2
    ("Chatto and Windus", "TIER_2", ["Chatto & Windus"]),
    ("George Allen", "TIER_2", []),
    ("Cassell, Petter & Galpin", "TIER_2", ["Cassell"]),
    ("Routledge", "TIER_2", []),
    ("Ward, Lock & Co.", "TIER_2", ["Ward Lock"]),
    ("Hurst & Company", "TIER_2", []),
    ("Grosset & Dunlap", "TIER_2", []),
]


def upgrade() -> None:
    # Create table
    op.create_table(
        "publisher_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alias_name", sa.String(length=200), nullable=False),
        sa.Column("publisher_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["publisher_id"],
            ["publishers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publisher_aliases_alias_name",
        "publisher_aliases",
        ["alias_name"],
        unique=True,
    )

    # Seed data using raw SQL for reliability
    conn = op.get_bind()

    for canonical_name, tier, aliases in PUBLISHER_SEEDS:
        # Upsert publisher - check if exists
        result = conn.execute(
            sa.text("SELECT id FROM publishers WHERE name = :name"),
            {"name": canonical_name},
        )
        row = result.fetchone()

        if row:
            publisher_id = row[0]
            # Update tier if needed
            conn.execute(
                sa.text(
                    "UPDATE publishers SET tier = :tier "
                    "WHERE id = :id AND (tier IS NULL OR tier != :tier)"
                ),
                {"tier": tier, "id": publisher_id},
            )
        else:
            result = conn.execute(
                sa.text(
                    "INSERT INTO publishers (name, tier, preferred) "
                    "VALUES (:name, :tier, false) RETURNING id"
                ),
                {"name": canonical_name, "tier": tier},
            )
            publisher_id = result.fetchone()[0]

        # Insert canonical name as alias (for consistent lookup)
        conn.execute(
            sa.text(
                "INSERT INTO publisher_aliases (alias_name, publisher_id) "
                "VALUES (:alias, :pub_id) "
                "ON CONFLICT (alias_name) DO NOTHING"
            ),
            {"alias": canonical_name, "pub_id": publisher_id},
        )

        # Insert variant aliases
        for alias in aliases:
            conn.execute(
                sa.text(
                    "INSERT INTO publisher_aliases (alias_name, publisher_id) "
                    "VALUES (:alias, :pub_id) "
                    "ON CONFLICT (alias_name) DO NOTHING"
                ),
                {"alias": alias, "pub_id": publisher_id},
            )


def downgrade() -> None:
    op.drop_index("ix_publisher_aliases_alias_name", table_name="publisher_aliases")
    op.drop_table("publisher_aliases")
