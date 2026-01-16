# Session Log: Issue #928 - SQL Refactor

**Date:** 2026-01-08
**Issue:** #928 - refactor: Eliminate duplicated SQL between migrations and health.py

## Summary

Refactor to eliminate duplicated SQL between Alembic migration files and health.py, establishing a single source of truth.

## User Requirements

1. PRs should be reviewed before going to staging and production
2. Use TDD approach
3. Maximize parallelism with subagents and worktrees for isolated work
4. Follow staging-first workflow

## Issue Details

**Problem:** Migration SQL is duplicated in two places:

1. Alembic migration files
2. health.py (for `/health/migrate` endpoint)

**Proposed Solutions from Issue:**

1. Extract to shared constants module
2. Generate health.py SQL from migration files with CI validation

**Acceptance Criteria:**

- [x] Single source of truth for migration SQL
- [x] CI validation that health.py stays in sync with migrations
- [x] No duplicate SQL definitions

## Progress Log

### Phase 1: Planning

- [x] Explore current codebase structure
- [x] Create implementation plan
- [x] Get user approval

### Phase 2: Implementation

- [x] Created `backend/app/db/migration_sql.py` as single source of truth
- [x] Updated health.py to import from migration_sql.py (reduced by ~490 lines)
- [x] Updated validation script to check migration_sql.py
- [x] CI validation already in place via `scripts/validate-migration-sync.sh`

## Implementation Details

### Files Changed

1. **`backend/app/db/migration_sql.py`** (NEW)
   - Single source of truth for all migration SQL
   - Contains `MIGRATIONS` dictionary with revision IDs as keys
   - Each migration has `upgrade` and `downgrade` SQL strings
   - Includes helper function `get_migration_sql(revision_id, direction)`

2. **`backend/app/routers/health.py`**
   - Removed ~490 lines of duplicated SQL
   - Now imports from `migration_sql.py`
   - Uses `get_migration_sql()` to retrieve SQL for `/health/migrate` endpoint

3. **`scripts/validate-migration-sync.sh`**
   - Updated to check `backend/app/db/migration_sql.py` instead of health.py
   - Same validation logic: ensures all migrations exist in the source of truth

### How to Add New Migrations

1. **Create Alembic migration file:**

   ```bash
   cd backend
   poetry run alembic revision -m "your migration description"
   ```

2. **Add SQL to migration_sql.py:**

   ```python
   # In backend/app/db/migration_sql.py
   MIGRATIONS["abc123def456"] = {
       "upgrade": """
           -- Your upgrade SQL here
       """,
       "downgrade": """
           -- Your downgrade SQL here
       """,
   }
   ```

3. **Use SQL in Alembic migration:**

   ```python
   # In the new migration file
   from app.db.migration_sql import get_migration_sql

   def upgrade():
       op.execute(get_migration_sql("abc123def456", "upgrade"))

   def downgrade():
       op.execute(get_migration_sql("abc123def456", "downgrade"))
   ```

4. **CI will validate:** The validation script runs in CI and will fail if:
   - A migration file exists without corresponding entry in migration_sql.py
   - SQL is defined in migration_sql.py but not used in migration files

### Benefits

- **Single source of truth:** SQL defined once in `migration_sql.py`
- **No drift:** CI validation catches any desync immediately
- **Reduced code:** health.py reduced by ~490 lines
- **Easier maintenance:** Only one place to update SQL

---

## Session Notes

### Plans Created

1. **SQL Duplication Refactor (#928)**: `docs/plans/2026-01-08-sql-duplication-refactor.md`
   - 6 tasks, TDD approach
   - Creates `backend/app/db/migration_sql.py` as single source of truth
   - Reduces health.py by ~400 lines
   - Adds CI validation

2. **Error Handling Refactor (#865)**: `docs/plans/2026-01-08-error-handling-refactor.md`
   - 8 tasks in 3 phases
   - Creates custom exception hierarchy in `backend/app/utils/errors.py`
   - Refactors books.py, users.py, images.py, listings.py
   - Adds error handling documentation

### Execution Strategy

These are independent refactors - can run in parallel using worktrees.
