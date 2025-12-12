"""add_admin_config_table

Revision ID: 9d7720474d6d
Revises: e18f8c3b2af7
Create Date: 2025-12-12 10:21:44.296431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9d7720474d6d'
down_revision: Union[str, None] = 'e18f8c3b2af7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'admin_config',
        sa.Column('key', sa.String(50), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    # Seed default values
    op.execute("""
        INSERT INTO admin_config (key, value) VALUES
        ('gbp_to_usd_rate', '1.28'),
        ('eur_to_usd_rate', '1.10')
    """)


def downgrade() -> None:
    op.drop_table('admin_config')
