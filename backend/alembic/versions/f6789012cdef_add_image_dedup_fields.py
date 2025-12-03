"""add_image_dedup_fields

Add original_filename and content_hash columns to book_images table
for duplicate detection.

Revision ID: f6789012cdef
Revises: e5f67890abcd
Create Date: 2025-12-02 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6789012cdef'
down_revision: Union[str, None] = 'e5f67890abcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add original_filename and content_hash columns to book_images."""
    op.add_column('book_images', sa.Column('original_filename', sa.String(255), nullable=True))
    op.add_column('book_images', sa.Column('content_hash', sa.String(64), nullable=True))

    # Add index on content_hash for fast duplicate lookups
    op.create_index('ix_book_images_content_hash', 'book_images', ['book_id', 'content_hash'])


def downgrade() -> None:
    """Remove original_filename and content_hash columns from book_images."""
    op.drop_index('ix_book_images_content_hash', table_name='book_images')
    op.drop_column('book_images', 'content_hash')
    op.drop_column('book_images', 'original_filename')
