"""Tests for migration SQL constants module."""


def test_migration_sql_module_exists():
    """The migration_sql module should be importable."""
    from app.db import migration_sql
    assert migration_sql is not None


def test_migration_sql_has_all_migrations():
    """All migration constants should be defined."""
    from app.db.migration_sql import MIGRATIONS

    # 35 migrations expected (includes duplicate s2345678klmn for different purposes)
    assert len(MIGRATIONS) == 35

    # Each migration should have id, name, and sql_statements
    for migration in MIGRATIONS:
        assert "id" in migration
        assert "name" in migration
        assert "sql_statements" in migration
        assert isinstance(migration["sql_statements"], list)


def test_specific_migrations_exist():
    """Spot-check specific known migrations exist."""
    from app.db.migration_sql import MIGRATIONS

    migration_ids = {m["id"] for m in MIGRATIONS}

    # Check a few known migrations from health.py
    assert "e44df6ab5669" in migration_ids  # acquisition columns
    assert "a1234567bcde" in migration_ids  # analysis_jobs table
    assert "57f0cff7af60" in migration_ids  # unique active job constraints


def test_tables_with_sequences_constant():
    """TABLES_WITH_SEQUENCES should be defined."""
    from app.db.migration_sql import TABLES_WITH_SEQUENCES

    assert len(TABLES_WITH_SEQUENCES) == 8
    assert "books" in TABLES_WITH_SEQUENCES


def test_cleanup_orphans_sql_constant():
    """CLEANUP_ORPHANS_SQL should be defined."""
    from app.db.migration_sql import CLEANUP_ORPHANS_SQL

    assert len(CLEANUP_ORPHANS_SQL) == 5
    assert all(isinstance(s, str) for s in CLEANUP_ORPHANS_SQL)
