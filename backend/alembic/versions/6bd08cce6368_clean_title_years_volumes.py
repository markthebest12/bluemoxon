"""clean_title_years_volumes

Remove redundant years and volume counts from book titles.
These values exist in separate database columns (publication_date, volumes).

Revision ID: 6bd08cce6368
Revises: a1b2c3d4e5f6
Create Date: 2025-12-01 16:09:08.639502

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '6bd08cce6368'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Title updates: (id, old_title, new_title)
TITLE_UPDATES = [
    (335, "Tennyson Complete Poetical Works (Moxon 9-vol)", "Tennyson Complete Poetical Works (Moxon)"),
    (336, "Byron Complete Poetical Works (Murray 8-vol)", "Byron Complete Poetical Works (Murray)"),
    (345, "The Popular Educator (Cassell 1870s)", "The Popular Educator (Cassell)"),
    (376, "Masters in Art 6 vols Bates & Guild", "Masters in Art"),
    (377, "Dickens Works 3 vols 1880s", "Dickens Works"),
]


def upgrade() -> None:
    """Update book titles to remove redundant years and volume counts."""
    connection = op.get_bind()

    for book_id, old_title, new_title in TITLE_UPDATES:
        # Only update if the title matches (in case it was already updated)
        connection.execute(
            text("UPDATE books SET title = :new_title WHERE id = :book_id AND title = :old_title"),
            {"book_id": book_id, "old_title": old_title, "new_title": new_title}
        )


def downgrade() -> None:
    """Restore original titles with years and volume counts."""
    connection = op.get_bind()

    for book_id, old_title, new_title in TITLE_UPDATES:
        connection.execute(
            text("UPDATE books SET title = :old_title WHERE id = :book_id AND title = :new_title"),
            {"book_id": book_id, "old_title": old_title, "new_title": new_title}
        )
