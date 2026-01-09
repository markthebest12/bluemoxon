#!/usr/bin/env python3
# ruff: noqa: T201
"""Validate that all Alembic migrations are registered in migration_sql.py.

This script prevents the recurring bug where Alembic migrations are created
but the migration_sql.py module isn't updated, causing deployed APIs to fail
with missing column errors.

Exit codes:
    0 - All migrations are synced
    1 - Missing migrations found
"""

import importlib.util
import re
import sys
from pathlib import Path

# Import migration_sql directly to avoid app.db package initialization
# which has dependencies on boto3 and other packages
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

spec = importlib.util.spec_from_file_location(
    "migration_sql", backend_dir / "app" / "db" / "migration_sql.py"
)
migration_sql = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_sql)
MIGRATIONS = migration_sql.MIGRATIONS


def get_alembic_revisions(versions_dir: Path) -> dict[str, str]:
    """Extract revision IDs and descriptions from Alembic migration files."""
    revisions = {}
    for file in versions_dir.glob("*.py"):
        if file.name == "__pycache__":
            continue
        # Parse filename pattern: {revision_id}_{description}.py
        match = re.match(r"([a-z0-9]+)_(.+)\.py", file.name)
        if match:
            revision_id = match.group(1)
            description = match.group(2)
            revisions[revision_id] = description
    return revisions


def get_excluded_revisions() -> set[str]:
    """Revisions that don't need migration_sql.py SQL.

    These are either:
    - Initial schema (tables created via init)
    - Legacy migrations applied before health.py migration system existed
    - Data-only migrations that don't change schema
    """
    return {
        # Initial schema
        "c929391b3002",  # initial_schema - tables created via init
        # Legacy migrations (applied before health.py migration system)
        "6bd08cce6368",  # clean_title_years_volumes - data cleanup
        "7ab2385590c1",  # increase_percentage_column_precision
        "a1b2c3d4e5f6",  # add_api_keys_table
        "d4e5f6789abc",  # add_user_name_fields
        "e18f8c3b2af7",  # add_archive_fields
        "e5f67890abcd",  # add_mfa_exempt_to_users
        "f6789012cdef",  # add_image_dedup_fields
    }


def main():
    versions_dir = backend_dir / "alembic" / "versions"

    if not versions_dir.exists():
        print(f"ERROR: Alembic versions directory not found: {versions_dir}")
        sys.exit(1)

    # Get all Alembic revisions
    alembic_revisions = get_alembic_revisions(versions_dir)
    print(f"Found {len(alembic_revisions)} Alembic migrations")

    # Get registered migration IDs from migration_sql.py
    registered_ids = {m["id"] for m in MIGRATIONS}
    print(f"Found {len(registered_ids)} unique migrations registered in migration_sql.py")

    # Get exclusions
    excluded = get_excluded_revisions()

    # Find missing migrations
    missing = []
    for revision_id, description in sorted(alembic_revisions.items()):
        if revision_id in excluded:
            continue
        if revision_id not in registered_ids:
            missing.append((revision_id, description))

    if missing:
        print("\nERROR: The following Alembic migrations are NOT registered in migration_sql.py:")
        print("=" * 70)
        for revision_id, description in missing:
            print(f"  - {revision_id}: {description}")
        print("=" * 70)
        print("\nTo fix: Add migration SQL to backend/app/db/migration_sql.py")
        print("Pattern: MIGRATION_{REVISION_ID_UPPERCASE}_SQL = [...]")
        print('Then add to MIGRATIONS list: {"id": "...", "name": "...", "sql_statements": ...}')
        print("\nSee existing migrations in migration_sql.py for examples.")
        sys.exit(1)

    print("\nAll Alembic migrations are registered in migration_sql.py")
    sys.exit(0)


if __name__ == "__main__":
    main()
