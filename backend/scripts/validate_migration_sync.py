#!/usr/bin/env python3
# ruff: noqa: T201
"""Validate that all Alembic migrations have corresponding SQL in health.py.

This script prevents the recurring bug where Alembic migrations are created
but the health.py /health/migrate endpoint isn't updated, causing deployed
APIs to fail with missing column errors.

Exit codes:
    0 - All migrations are synced
    1 - Missing migrations found
"""

import re
import sys
from pathlib import Path


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


def get_health_migrations(health_file: Path) -> set[str]:
    """Extract registered migration IDs from health.py."""
    content = health_file.read_text()

    # Find all migration IDs in the migrations list
    # Pattern: ("revision_id", MIGRATION_...) or ("revision_id", None)
    migrations_match = re.search(r"migrations\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not migrations_match:
        print("ERROR: Could not find migrations list in health.py")
        sys.exit(1)

    migrations_block = migrations_match.group(1)
    registered = set()

    # Extract revision IDs from tuples like ("e44df6ab5669", ...)
    for match in re.finditer(r'\("([a-z0-9]+)"', migrations_block):
        registered.add(match.group(1))

    return registered


def get_excluded_revisions() -> set[str]:
    """Revisions that don't need health.py SQL.

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
    # Find project root
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent

    versions_dir = backend_dir / "alembic" / "versions"
    health_file = backend_dir / "app" / "api" / "v1" / "health.py"

    if not versions_dir.exists():
        print(f"ERROR: Alembic versions directory not found: {versions_dir}")
        sys.exit(1)

    if not health_file.exists():
        print(f"ERROR: Health file not found: {health_file}")
        sys.exit(1)

    # Get all Alembic revisions
    alembic_revisions = get_alembic_revisions(versions_dir)
    print(f"Found {len(alembic_revisions)} Alembic migrations")

    # Get registered health.py migrations
    health_migrations = get_health_migrations(health_file)
    print(f"Found {len(health_migrations)} migrations registered in health.py")

    # Get exclusions
    excluded = get_excluded_revisions()

    # Find missing migrations
    missing = []
    for revision_id, description in sorted(alembic_revisions.items()):
        if revision_id in excluded:
            continue
        if revision_id not in health_migrations:
            missing.append((revision_id, description))

    if missing:
        print("\nERROR: The following Alembic migrations are NOT registered in health.py:")
        print("=" * 70)
        for revision_id, description in missing:
            print(f"  - {revision_id}: {description}")
        print("=" * 70)
        print("\nTo fix: Add migration SQL to backend/app/api/v1/health.py")
        print("Pattern: MIGRATION_{REVISION_ID_UPPERCASE}_SQL = [...]")
        print('Then register in migrations list: ("revision_id", MIGRATION_..._SQL)')
        print("\nSee existing migrations in health.py for examples.")
        sys.exit(1)

    print("\nAll Alembic migrations are registered in health.py")
    sys.exit(0)


if __name__ == "__main__":
    main()
