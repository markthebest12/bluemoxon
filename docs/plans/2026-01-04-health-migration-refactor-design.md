# Design: Extract SQL Migrations from health.py

**Date:** 2026-01-04
**Issue:** #801
**Status:** Approved

## Problem

`health.py` contains 800+ lines of hardcoded SQL migration constants that duplicate the existing Alembic migration files. The `/migrate` endpoint bypasses Alembic's migration system.

## Solution

Replace the hardcoded SQL with a programmatic call to `alembic.command.upgrade()`.

## Architecture

### File Structure After Refactor

```
health.py (1059 → ~250 lines)
├── Health check functions (check_database, check_s3, etc.)
├── Health endpoints (/live, /ready, /deep, /info, /version)
├── Migration endpoint (/migrate) - calls Alembic programmatically
└── Utility endpoints (/cleanup-orphans, /recalculate-discounts, /merge-binders)
```

### New /migrate Implementation

```python
from alembic import command
from alembic.config import Config

@router.post("/migrate")
async def run_migrations(db: Session = Depends(get_db)):
    """Run database migrations using Alembic."""
    # Get current version before migration
    current_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()

    # Configure Alembic programmatically
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", str(db.get_bind().url))

    # Run migrations
    command.upgrade(alembic_cfg, "head")

    # Get new version
    new_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()

    return {
        "status": "success",
        "previous_version": current_version,
        "new_version": new_version,
    }
```

### What Gets Deleted

- All 28 `MIGRATION_*_SQL` constants (lines 311-623)
- `TABLES_WITH_SEQUENCES` constant
- Complex SQL execution loop in `/migrate` endpoint

### What Stays

- `CLEANUP_ORPHANS_SQL` - used by `/cleanup-orphans` (database orphans, not migrations)
- All utility endpoints (`/cleanup-orphans`, `/recalculate-discounts`, `/merge-binders`)
- All health check functions and endpoints

## Testing Strategy

1. Write tests for new `/migrate` endpoint (TDD)
2. Verify existing tests pass after refactor
3. Manual validation in staging

## Risks & Mitigation

- **Risk:** Alembic path issues in Lambda
  - **Mitigation:** Use absolute path detection for `script_location`

- **Risk:** Database URL not available from session
  - **Mitigation:** Read from settings as fallback

## Implementation Plan

1. Create feature branch
2. Write tests for new /migrate endpoint
3. Implement new /migrate endpoint
4. Delete SQL constants
5. Run tests, lint, type-check
6. Create PR for review
