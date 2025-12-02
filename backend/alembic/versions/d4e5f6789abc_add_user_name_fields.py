"""add_user_name_fields

Add first_name and last_name columns to users table.

Revision ID: d4e5f6789abc
Revises: 6bd08cce6368
Create Date: 2025-12-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6789abc'
down_revision: Union[str, None] = '6bd08cce6368'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add first_name and last_name columns to users table."""
    op.add_column('users', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(100), nullable=True))


def downgrade() -> None:
    """Remove first_name and last_name columns from users table."""
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
