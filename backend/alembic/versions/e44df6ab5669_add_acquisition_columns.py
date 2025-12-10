"""add_acquisition_columns

Revision ID: e44df6ab5669
Revises: d4e5f6789abc
Create Date: 2025-12-10 11:38:53.570522

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e44df6ab5669'
down_revision: Union[str, None] = 'd4e5f6789abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('books', sa.Column('source_url', sa.String(500), nullable=True))
    op.add_column('books', sa.Column('source_item_id', sa.String(100), nullable=True))
    op.add_column('books', sa.Column('estimated_delivery', sa.Date(), nullable=True))
    op.add_column('books', sa.Column('scoring_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add index for source_item_id lookups
    op.create_index('books_source_item_id_idx', 'books', ['source_item_id'])


def downgrade() -> None:
    op.drop_index('books_source_item_id_idx', table_name='books')
    op.drop_column('books', 'scoring_snapshot')
    op.drop_column('books', 'estimated_delivery')
    op.drop_column('books', 'source_item_id')
    op.drop_column('books', 'source_url')
