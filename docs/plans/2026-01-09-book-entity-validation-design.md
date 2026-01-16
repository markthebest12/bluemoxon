# Book Endpoint Entity Validation - Design Document

**Issue:** #968 - Add entity validation to book endpoints (Phase 3 of #955)
**Date:** 2026-01-09
**Status:** Approved - Ready for Implementation

---

## Problem Statement

The `PUT /books/{book_id}/analysis` endpoint and async analysis worker auto-create entities via `get_or_create_binder()` and `get_or_create_publisher()`. This bypasses the Phase 2 validation added to entity creation endpoints, allowing duplicate/variant entities to proliferate.

---

## Solution

Add validation BEFORE entity association in book endpoints:

| Scenario | Response | Action Required |
|----------|----------|-----------------|
| Exact match exists | Success | Uses existing entity |
| Fuzzy match 80%+ | **409 Conflict** | Pick from suggestions or create new first |
| No match | **400 Bad Request** | Create entity first via dedicated endpoint |

---

## Architecture

### New Function: `validate_entity_for_book()`

Location: `backend/app/services/entity_validation.py`

```python
def validate_entity_for_book(
    db: Session,
    entity_type: EntityType,  # "publisher" | "binder" | "author"
    name: str,
    threshold: float | None = None,
) -> int | EntityValidationError:
    """
    Validate entity name before associating with a book.

    Returns:
        int: Entity ID if exact match found (safe to use)
        EntityValidationError: If similar match (409) or unknown (400)
    """
```

**Logic:**

1. Normalize the name (type-specific normalization)
2. Check for exact match in DB → return entity ID
3. Check for 80%+ fuzzy match → return 409 error with suggestions
4. No match at all → return 400 error ("create entity first")

---

## Code Changes

### 1. `books.py:update_book_analysis()`

Before:

```python
if parsed.binder_identification:
    binder = get_or_create_binder(db, parsed.binder_identification)
    if binder and book.binder_id != binder.id:
        book.binder_id = binder.id
```

After:

```python
if parsed.binder_identification and parsed.binder_identification.get("name"):
    binder_name = parsed.binder_identification["name"]
    result = validate_entity_for_book(db, "binder", binder_name)

    if isinstance(result, EntityValidationError):
        raise HTTPException(
            status_code=409 if result.error == "similar_entity_exists" else 400,
            detail=result.model_dump(),
        )

    if result and book.binder_id != result:
        book.binder_id = result
```

Same pattern for publisher validation.

### 2. `worker.py:process_analysis_job()`

Worker fails job with descriptive error when validation fails:

```python
if parsed.binder_identification and parsed.binder_identification.get("name"):
    binder_name = parsed.binder_identification["name"]
    result = validate_entity_for_book(db, "binder", binder_name)

    if isinstance(result, EntityValidationError):
        raise EntityValidationJobError(result)

    if result and book.binder_id != result:
        book.binder_id = result
```

---

## Error Response Format

**409 Conflict (similar exists):**

```json
{
  "error": "similar_entity_exists",
  "entity_type": "binder",
  "input": "Bayntun (of Bath)",
  "suggestions": [{"id": 5, "name": "Bayntun", "tier": "TIER_1", "match": 0.88, "book_count": 12}],
  "resolution": "Use existing binder ID, or create new via POST /binders?force=true"
}
```

**400 Bad Request (unknown):**

```json
{
  "error": "unknown_entity",
  "entity_type": "publisher",
  "input": "Totally New Press",
  "suggestions": null,
  "resolution": "Create via POST /publishers first, then retry analysis upload"
}
```

**Worker job error message:**

```text
Entity validation failed: binder 'Bayntun (of Bath)' matches existing
'Bayntun' (88%). Use existing ID or create new via POST /binders?force=true
```

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/services/entity_validation.py` | Add `validate_entity_for_book()` |
| `backend/app/api/v1/books.py` | Update `update_book_analysis()` |
| `backend/app/worker.py` | Update `process_analysis_job()` |
| `backend/tests/services/test_entity_validation.py` | Add validation tests |
| `backend/tests/api/v1/test_books.py` | Add endpoint tests |
| `backend/tests/test_worker.py` | Add worker tests |

---

## Testing Strategy

**Unit tests:**

- Exact match → returns entity ID
- 80%+ fuzzy match → returns 409 error
- No match → returns 400 error
- Empty/None name → returns None

**Integration tests:**

- Analysis with known entity → associates correctly
- Analysis with similar entity (88%) → 409 with suggestions
- Analysis with unknown entity → 400 with resolution
- Worker job validation failures → job fails with message

---

## Implementation Order

1. Write tests for `validate_entity_for_book()`
2. Implement `validate_entity_for_book()`
3. Write tests for `update_book_analysis()` validation
4. Update `books.py`
5. Write tests for worker validation
6. Update `worker.py`
7. Run full test suite, create PR

---

*Design approved: 2026-01-09*
