"""seed_author_publisher_binder_tiers

Revision ID: f4f2fbe81faa
Revises: s2345678klmn
Create Date: 2025-12-21 19:09:32.867717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4f2fbe81faa'
down_revision: Union[str, None] = 's2345678klmn'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Author tiers
    op.execute("UPDATE authors SET tier = 'TIER_1' WHERE id = 34")  # Darwin
    op.execute("UPDATE authors SET tier = 'TIER_2' WHERE id = 250")  # Dickens
    op.execute("UPDATE authors SET tier = 'TIER_2' WHERE id = 335")  # Collins
    op.execute("UPDATE authors SET tier = 'TIER_3' WHERE id = 260")  # Ruskin

    # Create Lyell if not exists, set to TIER_1
    op.execute("""
        INSERT INTO authors (name, tier, birth_year, death_year, era)
        VALUES ('Charles Lyell', 'TIER_1', 1797, 1875, 'Victorian')
        ON CONFLICT (name) DO UPDATE SET tier = 'TIER_1'
    """)

    # Publisher tiers
    op.execute("UPDATE publishers SET tier = 'TIER_2' WHERE id = 193")  # Chatto and Windus
    op.execute("UPDATE publishers SET tier = 'TIER_2' WHERE id = 197")  # George Allen

    # Binder tiers
    op.execute("UPDATE binders SET tier = 'TIER_1' WHERE id = 4")  # Bayntun
    op.execute("UPDATE binders SET tier = 'TIER_1' WHERE id = 27")  # Leighton

    # Create Hayday binder
    op.execute("""
        INSERT INTO binders (name, tier)
        VALUES ('Hayday', 'TIER_1')
        ON CONFLICT (name) DO UPDATE SET tier = 'TIER_1'
    """)


def downgrade() -> None:
    # Revert author tiers
    op.execute("UPDATE authors SET tier = NULL WHERE id IN (34, 250, 335, 260)")
    op.execute("DELETE FROM authors WHERE name = 'Charles Lyell'")

    # Revert publisher tiers
    op.execute("UPDATE publishers SET tier = NULL WHERE id IN (193, 197)")

    # Revert binder tiers
    op.execute("UPDATE binders SET tier = 'TIER_2' WHERE id = 4")  # Bayntun was TIER_2
    op.execute("UPDATE binders SET tier = NULL WHERE id = 27")
    op.execute("DELETE FROM binders WHERE name = 'Hayday'")
