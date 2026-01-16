# Database Sequence Reset for Staging Sync

**Date:** 2025-12-09
**Status:** Approved

## Problem

The db_sync Lambda copies data from prod to staging but intentionally skips `nextval` sequence defaults (handler.py line 156). This breaks INSERTs on staging because `id` columns have no auto-increment capability.

**Error seen:** `null value in column "id" of relation "books" violates not-null constraint`

## Use Case

Periodic refresh - regularly sync prod to staging to keep data fresh. After each sync, staging needs working sequences for INSERT operations (testing new features, etc.).

## Solution

### Part 1: Immediate Fix - Temporary Admin Endpoint

Add a protected admin endpoint to the main API Lambda to reset sequences now.

**Endpoint:** `POST /api/v1/admin/reset-sequences`
**Security:** Requires valid API key (`X-API-Key` header)
**Location:** `backend/app/api/v1/admin.py`

**Behavior:**

1. Query all tables with serial/identity columns
2. For each table, get sequence name via `pg_get_serial_sequence()`
3. Set sequence to `COALESCE(MAX(id), 0) + 1`
4. Return summary of sequences reset

### Part 2: Permanent Fix - db_sync Handler Update

Add `reset_sequences()` function to `backend/lambdas/db_sync/handler.py`.

**Integration:** Called automatically at end of `sync_databases()` after validation.

**Function:**

```python
def reset_sequences(conn) -> list[dict]:
    """Reset all sequences to MAX(id) + 1 after data sync."""
    results = []
    with conn.cursor() as cur:
        # Find all serial columns
        cur.execute("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_default LIKE 'nextval%'
        """)
        serial_columns = cur.fetchall()

        for table, column in serial_columns:
            seq_name = f"{table}_{column}_seq"
            cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', '{column}'),
                    COALESCE((SELECT MAX({column}) FROM {table}), 0) + 1,
                    false
                )
            """)
            new_val = cur.fetchone()[0]
            results.append({"table": table, "column": column, "sequence": seq_name, "value": new_val})

    conn.commit()
    return results
```

**Result tracking:** Add `sequences_reset` to sync results.

### Part 3: Cleanup

After db_sync update is deployed and verified:

1. Remove `POST /api/v1/admin/reset-sequences` endpoint
2. Remove admin router from `backend/app/api/v1/__init__.py`
3. Delete `backend/app/api/v1/admin.py`

Tracked in issue #155.

## Implementation Order

1. Create admin endpoint in main API
2. Deploy to staging
3. Call endpoint to fix sequences
4. Verify POSTs work (book-collection project)
5. Update db_sync handler with `reset_sequences()`
6. Redeploy db-sync Lambda
7. Run fresh sync, verify sequences work automatically
8. Remove temp admin endpoint (cleanup)

## Files Changed

**New (temporary):**

- `backend/app/api/v1/admin.py`

**Modified:**

- `backend/app/api/v1/__init__.py` (add admin router)
- `backend/lambdas/db_sync/handler.py` (add reset_sequences)
