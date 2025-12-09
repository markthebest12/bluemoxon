"""Admin endpoints for database maintenance operations.

TEMPORARY: This module will be removed after db_sync handler is updated
to reset sequences automatically. Tracked in issue #155.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_admin
from app.db import get_db

router = APIRouter()


@router.post("/fix-sequences")
async def fix_sequences(
    _user: Annotated[CurrentUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> dict:
    """Fix sequences for all tables with integer primary key columns.

    This handles the case where db_sync skipped the nextval defaults:
    1. Creates sequence if it doesn't exist
    2. Sets column default to use the sequence
    3. Resets sequence value to MAX(id) + 1

    Requires admin authentication (API key or admin user).
    """
    results = []

    # Find all tables with integer 'id' columns that are primary keys
    # This catches both cases: columns with nextval defaults and those without
    id_columns_query = text("""
        SELECT
            c.table_name,
            c.column_name,
            c.column_default
        FROM information_schema.columns c
        JOIN information_schema.table_constraints tc
            ON c.table_name = tc.table_name
            AND c.table_schema = tc.table_schema
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND c.column_name = kcu.column_name
            AND c.table_name = kcu.table_name
        WHERE c.table_schema = 'public'
          AND tc.constraint_type = 'PRIMARY KEY'
          AND c.data_type IN ('integer', 'bigint')
        ORDER BY c.table_name, c.column_name
    """)

    id_columns = db.execute(id_columns_query).fetchall()

    for table_name, column_name, current_default in id_columns:
        seq_name = f"{table_name}_{column_name}_seq"
        action = "reset"

        # If no nextval default exists, we need to create the sequence and set the default
        if not current_default or "nextval" not in str(current_default):
            action = "created"
            # Create sequence if it doesn't exist
            # Safe: table_name and column_name come from information_schema, admin-only endpoint
            create_seq_sql = f'CREATE SEQUENCE IF NOT EXISTS "{seq_name}"'  # noqa: S608 # nosec B608
            db.execute(text(create_seq_sql))  # fmt: skip # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text

            # Set the column default to use the sequence
            alter_sql = f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" SET DEFAULT nextval(\'{seq_name}\')'  # noqa: S608 # nosec B608
            db.execute(text(alter_sql))  # fmt: skip # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text

            # Set sequence ownership so it's dropped with the table
            owner_sql = f'ALTER SEQUENCE "{seq_name}" OWNED BY "{table_name}"."{column_name}"'  # noqa: S608 # nosec B608
            db.execute(text(owner_sql))  # fmt: skip # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text

        # Reset sequence to MAX(id) + 1
        reset_sql = f'SELECT setval(\'{seq_name}\', COALESCE((SELECT MAX("{column_name}") FROM "{table_name}"), 0) + 1, false)'  # noqa: S608 # nosec B608
        result = db.execute(text(reset_sql)).fetchone()  # fmt: skip # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text

        new_value = result[0] if result else None

        results.append(
            {
                "table": table_name,
                "column": column_name,
                "sequence": seq_name,
                "new_value": new_value,
                "action": action,
            }
        )

    db.commit()

    return {
        "message": f"Fixed {len(results)} sequences",
        "sequences": results,
    }
