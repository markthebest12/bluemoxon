# Postmortem: Cleanup Lambda S3 Mass Deletion

**Date:** 2025-12-30
**Status:** Resolved
**Severity:** Critical - Data Loss in Staging
**Resolution:** PR #686 (staging), PR #691 (production)
**Related Issues:** #189, #190, #191

---

## Executive Summary

The cleanup Lambda's `cleanup_orphaned_images` function deleted ~6,892 objects from the staging S3 bucket, including non-image files (lambda packages, listings data, prompts, etc.). The function was designed to find orphaned book images but lacked prefix filtering, causing it to treat ALL non-BookImage files as orphans.

**Impact:**
- 5,089 files in `books/` prefix deleted
- 1,486 files in `listings/` prefix deleted
- 300 files in `images/` prefix deleted
- Lambda deployment packages, prompts, and other data deleted

---

## Root Cause Analysis

### Primary Cause: Key Format Mismatch

S3 stores images with `books/` prefix, but database stores keys WITHOUT the prefix:

```python
# S3 stores: "books/515/image_00.webp"
# DB stores: "515/image_00.webp"

# BUG: Direct comparison never matches
orphaned_keys = s3_keys - db_keys  # ALL S3 keys appear orphaned!
```

### Secondary Cause: No S3 Prefix Filter

The function lists ALL objects in the bucket without filtering:

```python
# BUG: Lists entire bucket
for page in paginator.paginate(Bucket=bucket):
    for obj in page.get("Contents", []):
        s3_keys.add(obj["Key"])
```

Should be:

```python
# FIX: Only list objects in books/ prefix
for page in paginator.paginate(Bucket=bucket, Prefix="books/"):
    for obj in page.get("Contents", []):
        s3_keys.add(obj["Key"])
```

### Contributing Cause: Insufficient Dry Run Output

The dry run returned only a count with no context:

```json
{"orphans_found": 6892}
```

This count is meaningless without knowing:
- Total objects in bucket
- Expected prefix being scanned
- Breakdown by prefix

If 6,892 is orphans but total objects is 7,000, that's a 98% orphan rate - an obvious red flag. But the output provided no way to detect this.

---

## Fix Implementation Approach

### 1. Add Prefix Filtering and Key Stripping (Required)

```python
S3_BOOKS_PREFIX = "books/"

def cleanup_orphaned_images(
    db: Session,
    bucket: str,
    delete: bool = False
) -> dict:
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    s3_keys_full = set()      # Full keys for deletion
    s3_keys_stripped = set()  # Stripped keys for comparison

    for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
        for obj in page.get("Contents", []):
            full_key = obj["Key"]
            s3_keys_full.add(full_key)
            # Strip prefix to match DB format
            if full_key.startswith(S3_BOOKS_PREFIX):
                s3_keys_stripped.add(full_key[len(S3_BOOKS_PREFIX):])

    # Compare stripped keys to DB keys
    orphaned_stripped = s3_keys_stripped - db_keys
    # Convert back to full keys for deletion
    orphaned_full_keys = {f"{S3_BOOKS_PREFIX}{k}" for k in orphaned_stripped}
```

### 2. Enhanced Dry Run Output (Required)

Return contextual information that makes anomalies obvious:

```python
def cleanup_orphaned_images(...) -> dict:
    # ... scanning logic ...

    # Group orphans by top-level prefix for visibility
    orphans_by_prefix = {}
    for key in orphaned_full_keys:
        prefix = key.split("/")[0] + "/" if "/" in key else "(root)"
        orphans_by_prefix[prefix] = orphans_by_prefix.get(prefix, 0) + 1

    # Build contextual response
    result = {
        "scan_prefix": S3_BOOKS_PREFIX,
        "total_objects_scanned": len(s3_keys_full),
        "objects_in_database": len(db_keys),
        "orphans_found": len(orphaned_full_keys),
        "orphans_by_prefix": orphans_by_prefix,
        "orphan_percentage": round(len(orphaned_full_keys) / len(s3_keys_full) * 100, 1) if s3_keys_full else 0,
        "sample_orphan_keys": list(orphaned_full_keys)[:10],  # Capped for response size
        "deleted": deleted,
    }

    # Add warning if high orphan rate
    if result["orphan_percentage"] > 50:
        result["WARNING"] = f"High orphan rate ({result['orphan_percentage']}%) - verify before deleting"

    return result
```

### 3. Example Output After Fix

**Before (useless):**
```json
{
  "orphans_found": 6892,
  "orphans_deleted": 0
}
```

**After (actionable):**
```json
{
  "scan_prefix": "books/",
  "total_objects_scanned": 5089,
  "objects_in_database": 5074,
  "orphans_found": 15,
  "orphan_percentage": 0.3,
  "orphans_by_prefix": {
    "books/": 15
  },
  "sample_orphan_keys": [
    "books/orphan1/photo.jpg",
    "books/orphan2/photo.jpg"
  ],
  "deleted": 0
}
```

If the key mismatch bug existed, the output would reveal it:
```json
{
  "scan_prefix": "books/",
  "total_objects_scanned": 5089,
  "objects_in_database": 5089,
  "orphans_found": 5089,
  "orphan_percentage": 100.0,
  "orphans_by_prefix": {
    "books/": 5089
  },
  "WARNING": "High orphan rate (100.0%) - verify before deleting"
}
```

### 4. Implementation Notes

- Prefix is hardcoded as `S3_BOOKS_PREFIX = "books/"` since this matches the actual S3 structure
- No configurable prefix needed - book images always live under `books/`
- The `orphans_by_prefix` breakdown provides visibility into what's being detected

---

## Preventive Measures

| Measure | Description |
|---------|-------------|
| Prefix filtering | Only scan configured prefix, never entire bucket |
| Contextual dry run | Show totals, percentages, prefix breakdown |
| Warnings | Alert on >50% orphan rate or unexpected prefixes |
| Sample output | Show actual keys being targeted for human review |
| Integration test | Test with mixed-prefix bucket to catch regressions |

---

## Verification Checklist

Before re-enabling orphan cleanup:

- [ ] Prefix filter implemented and tested
- [ ] Dry run shows contextual breakdown
- [ ] Warnings trigger for unexpected conditions
- [ ] Integration test covers multi-prefix bucket
- [ ] Staging data restored and cleanup re-verified
- [ ] Documentation updated with safe usage examples

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/lambdas/cleanup/handler.py` | Add prefix filter, enhance dry run output |
| `backend/tests/test_cleanup.py` | Add tests for prefix filtering and output format |
| `docs/postmortems/2025-12-30-cleanup-lambda-s3-deletion.md` | This postmortem document |
