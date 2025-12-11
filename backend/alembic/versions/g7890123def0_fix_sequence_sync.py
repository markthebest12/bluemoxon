"""fix_sequence_sync

Reset all PostgreSQL sequences to match max id values.
This fixes issues caused by data sync/import where sequences
get out of sync with actual data.

Revision ID: g7890123def0
Revises: f6789012cdef
Create Date: 2025-12-11 09:00:00.000000

"""
from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'g7890123def0'
down_revision: str | None = 'f6789012cdef'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables with auto-increment sequences that need syncing
TABLES_WITH_SEQUENCES = [
    'authors',
    'api_keys',
    'binders',
    'book_analyses',
    'book_images',
    'books',
    'publishers',
    'users',
]


def upgrade() -> None:
    """Reset all sequences to max(id) + 1."""
    connection = op.get_bind()

    # Check if we're on PostgreSQL (SQLite doesn't have sequences)
    if connection.dialect.name != 'postgresql':
        return

    for table in TABLES_WITH_SEQUENCES:
        # Use setval to reset the sequence
        # setval(seq, max(id)) sets the sequence so NEXT call returns max(id)+1
        # Table names are from hardcoded constant TABLES_WITH_SEQUENCES, not user input
        # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
        connection.execute(text(f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table}), 0) + 1,
                false
            )
        """))  # noqa: S608


def downgrade() -> None:
    """No downgrade needed - sequences will auto-correct on next insert."""
    pass
