"""Tests for migration SQL constants module."""


def test_migration_sql_module_exists():
    """The migration_sql module should be importable."""
    from app.db import migration_sql

    assert migration_sql is not None


def test_migration_ids_are_unique():
    """P0 CRITICAL: Every migration ID must be unique.

    Duplicate IDs cause silent failures - the set() in validators masks them,
    but /health/migrate would run the same ID twice with different SQL.
    """
    from app.db.migration_sql import MIGRATIONS

    ids = [m["id"] for m in MIGRATIONS]
    duplicates = [mid for mid in ids if ids.count(mid) > 1]

    assert len(duplicates) == 0, f"Duplicate migration IDs found: {set(duplicates)}"
    assert len(ids) == len(set(ids)), "Migration IDs must be unique"


def test_migrations_have_required_structure():
    """Each migration must have id, name, and sql_statements."""
    from app.db.migration_sql import MIGRATIONS

    for i, migration in enumerate(MIGRATIONS):
        assert "id" in migration, f"Migration at index {i} missing 'id'"
        assert "name" in migration, f"Migration at index {i} missing 'name'"
        assert "sql_statements" in migration, f"Migration at index {i} missing 'sql_statements'"
        assert isinstance(migration["sql_statements"], list), (
            f"Migration {migration['id']} sql_statements must be a list"
        )
        assert isinstance(migration["id"], str), f"Migration at index {i} id must be string"
        assert isinstance(migration["name"], str), f"Migration at index {i} name must be string"
        assert len(migration["id"]) >= 8, (
            f"Migration {migration['name']} has suspiciously short id: {migration['id']}"
        )


def test_migrations_list_is_not_empty():
    """MIGRATIONS list must contain at least one migration."""
    from app.db.migration_sql import MIGRATIONS

    assert len(MIGRATIONS) > 0, "MIGRATIONS list is empty"


def test_specific_migrations_exist():
    """Spot-check specific known migrations exist."""
    from app.db.migration_sql import MIGRATIONS

    migration_ids = {m["id"] for m in MIGRATIONS}

    # Check a few known migrations - these are load-bearing
    assert "e44df6ab5669" in migration_ids, "acquisition columns migration missing"
    assert "a1234567bcde" in migration_ids, "analysis_jobs table migration missing"
    assert "57f0cff7af60" in migration_ids, "unique active job constraints migration missing"


def test_tables_with_sequences_has_required_tables():
    """TABLES_WITH_SEQUENCES must include core tables."""
    from app.db.migration_sql import TABLES_WITH_SEQUENCES

    assert isinstance(TABLES_WITH_SEQUENCES, list), "TABLES_WITH_SEQUENCES must be a list"
    assert len(TABLES_WITH_SEQUENCES) > 0, "TABLES_WITH_SEQUENCES is empty"

    # Core tables that must have sequences
    required = {"books", "authors", "publishers"}
    actual = set(TABLES_WITH_SEQUENCES)
    missing = required - actual
    assert not missing, f"Missing required tables in TABLES_WITH_SEQUENCES: {missing}"


def test_cleanup_orphans_sql_is_valid():
    """CLEANUP_ORPHANS_SQL must contain valid SQL statements."""
    from app.db.migration_sql import CLEANUP_ORPHANS_SQL

    assert isinstance(CLEANUP_ORPHANS_SQL, list), "CLEANUP_ORPHANS_SQL must be a list"
    assert len(CLEANUP_ORPHANS_SQL) > 0, "CLEANUP_ORPHANS_SQL is empty"
    assert all(isinstance(s, str) for s in CLEANUP_ORPHANS_SQL), (
        "All CLEANUP_ORPHANS_SQL entries must be strings"
    )
    # Each should be a DELETE statement
    for sql in CLEANUP_ORPHANS_SQL:
        assert "DELETE" in sql.upper(), f"Expected DELETE statement: {sql[:50]}..."


def test_empty_sql_statements_are_documented():
    """Migrations with empty sql_statements must have documented reason.

    Empty sql_statements silently do nothing in /health/migrate.
    Known intentional empties:
    - 44275552664d: Original condition_grade normalization that was incomplete,
                   re-run in dd7f743834bc. Kept for alembic_version ordering.
    - g7890123def0: Dynamic SQL (sequence sync) handled specially in health.py
    """
    from app.db.migration_sql import MIGRATIONS

    # Known intentional empty migrations
    intentional_empties = {
        "44275552664d",  # Re-run in dd7f743834bc
        "g7890123def0",  # Dynamic sequence sync SQL
    }

    for migration in MIGRATIONS:
        if len(migration["sql_statements"]) == 0:
            assert migration["id"] in intentional_empties, (
                f"Migration {migration['id']} ({migration['name']}) has empty sql_statements. "
                f"If intentional, add to intentional_empties with comment explaining why."
            )
