"""add_archive_fields

Revision ID: e18f8c3b2af7
Revises: h8901234efgh
Create Date: 2025-12-12 08:13:05.710587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e18f8c3b2af7'
down_revision: Union[str, None] = 'h8901234efgh'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('books', sa.Column('source_archived_url', sa.String(500), nullable=True))
    op.add_column('books', sa.Column('archive_status', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('books', 'archive_status')
    op.drop_column('books', 'source_archived_url')
