"""add_mfa_exempt_to_users

Add mfa_exempt column to users table for per-user MFA exemption.

Revision ID: e5f67890abcd
Revises: d4e5f6789abc
Create Date: 2025-12-02 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f67890abcd'
down_revision: Union[str, None] = 'd4e5f6789abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add mfa_exempt column to users table."""
    op.add_column('users', sa.Column('mfa_exempt', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove mfa_exempt column from users table."""
    op.drop_column('users', 'mfa_exempt')
