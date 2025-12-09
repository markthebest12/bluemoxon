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


@router.post("/reset-sequences")
async def reset_sequences(
    _user: Annotated[CurrentUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> dict:
    """Reset all sequences to MAX(id) + 1 for tables with serial columns.

    This is needed after db_sync copies data from prod to staging,
    since the sync skips sequence defaults.

    Requires admin authentication (API key or admin user).
    """
    results = []

    # Find all tables with serial/identity columns (columns with nextval defaults)
    serial_columns_query = text("""
        SELECT
            table_name,
            column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_default LIKE 'nextval%'
        ORDER BY table_name, column_name
    """)

    serial_columns = db.execute(serial_columns_query).fetchall()

    for table_name, column_name in serial_columns:
        # Get the sequence name and reset it
        # Safe: table_name and column_name come from information_schema, admin-only endpoint
        sql = f"SELECT setval(pg_get_serial_sequence(:table, :column), COALESCE((SELECT MAX({column_name}) FROM {table_name}), 0) + 1, false)"  # noqa: S608 # nosec B608
        reset_query = text(sql)  # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text

        result = db.execute(reset_query, {"table": table_name, "column": column_name}).fetchone()

        new_value = result[0] if result else None

        results.append(
            {
                "table": table_name,
                "column": column_name,
                "sequence": f"{table_name}_{column_name}_seq",
                "new_value": new_value,
            }
        )

    db.commit()

    return {
        "message": f"Reset {len(results)} sequences",
        "sequences": results,
    }
