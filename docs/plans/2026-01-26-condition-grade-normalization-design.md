# Design: Condition Grade Normalization Fix

**Issue:** #1333 - Book 648 shows "0 VG condition (below Good)" due to unnormalized condition_grade
**Date:** 2026-01-26

## Problem

Book 648 has `condition_grade: "VG"` instead of `"VERY_GOOD"`, causing scoring to show 0 points for condition.

### Root Cause

In `worker.py` lines 258-259, the Stage 2 extraction path directly assigns condition_grade from AI output without normalization:

```python
if extracted_data.get("condition_grade"):
    book_updates["condition_grade"] = extracted_data["condition_grade"]
```

The YAML fallback path correctly calls `normalize_condition_grade()`, but Stage 2 (the primary path for new analyses) does not.

## Solution

### 1. Code Fix in worker.py

Add normalization call in Stage 2 extraction path:

```python
if extracted_data.get("condition_grade"):
    from app.services.analysis_summary import normalize_condition_grade
    normalized = normalize_condition_grade(extracted_data["condition_grade"])
    if normalized:
        book_updates["condition_grade"] = normalized
```

### 2. One-Time Data Migration

Add health endpoint `/health/normalize-condition-grades` that:

1. Queries books with unnormalized condition_grade values:
   ```sql
   WHERE condition_grade IS NOT NULL
     AND condition_grade NOT IN ('FINE', 'NEAR_FINE', 'VERY_GOOD', 'GOOD', 'FAIR', 'POOR')
   ```
2. Normalizes each using `ConditionGrade.from_alias()`
3. Returns count of fixed records

Response format:
```json
{
  "normalized": 5,
  "skipped": 1,
  "details": [
    {"book_id": 648, "old": "VG", "new": "VERY_GOOD"}
  ]
}
```

### 3. Test Coverage

**Unit tests (test_worker.py):**
- Test "VG" → "VERY_GOOD" normalization
- Test "VERY_GOOD" passes through unchanged
- Test invalid "JUNK" is skipped

**Integration tests (test_health.py):**
- Test normalization works (VG → VERY_GOOD)
- Test NULLs untouched
- Test idempotency: second call returns `"normalized": 0`

## Implementation Steps

| Step | File | Change |
|------|------|--------|
| 1 | `backend/app/worker.py` | Add `normalize_condition_grade()` call |
| 2 | `backend/app/api/v1/health.py` | Add `/health/normalize-condition-grades` endpoint |
| 3 | `backend/tests/test_worker.py` | Add 3 unit tests |
| 4 | `backend/tests/test_health.py` | Add 3 integration tests |

## Deployment Sequence

1. PR to staging with all changes
2. Merge to staging
3. Call `/health/normalize-condition-grades` on staging
4. Verify book 648 shows correct condition score
5. PR staging → main
6. Call `/health/normalize-condition-grades` on production

## Related

- PR #1288: Added `normalize_condition_grade()` but missed Stage 2 path
- PR #1218: Fixed enum values in scoring.py
- Issue #1219: Fixed tiered_scoring.py enum values
