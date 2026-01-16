# Entity Proliferation Prevention - Design Document

**Issue:** Prevent uncontrolled creation of duplicate/variant binders, publishers, and authors
**Date:** 2026-01-09
**Status:** Design Complete - Ready for Implementation

---

## Problem Statement

Reference entities (publishers, binders, authors) proliferate when:

1. AI generates slight variations ("Bayntun (of Bath)" vs "Bayntun")
2. Manual entry introduces typos ("Macmilan" vs "Macmillan")
3. Different name formats used ("Dickens, Charles" vs "Charles Dickens")

Current protections are insufficient:

- Publishers: Fuzzy matching at 90% threshold, but unknown names still auto-created
- Binders: Hardcoded dict of known variants, unknown pass through
- Authors: No protection at all

---

## Solution: API-Level Validation with Friction at Creation

Force explicit decisions by rejecting ambiguous entity references at the API level.

### Design Principles

1. **ID references always work** - Using `publisher_id: 5` is never rejected
2. **String names require validation** - `publisher_name: "Foo"` triggers matching
3. **Similar matches require resolution** - Return 409 with suggestions
4. **Unknown names require explicit creation** - Return 400, must create via dedicated endpoint
5. **Force flag for intentional duplicates** - `?force=true` bypasses validation

---

## API Behavior Changes

### Book Endpoints (`POST/PUT /books`)

**When entity name (string) provided:**

| Scenario | Response | Action Required |
|----------|----------|-----------------|
| Exact match exists | 200/201 | Uses existing entity |
| Fuzzy match 80%+ | **409 Conflict** | Pick from suggestions or create new |
| No match | **400 Bad Request** | Create entity first via dedicated endpoint |

**Example - Similar entity exists:**

```text
POST /books
{
  "title": "Some Book",
  "publisher_name": "Macmilan"
}

Response: 409 Conflict
{
  "error": "similar_entity_exists",
  "entity_type": "publisher",
  "input": "Macmilan",
  "suggestions": [
    {"id": 5, "name": "Macmillan and Co.", "tier": "TIER_1", "match": 0.94, "book_count": 12}
  ],
  "resolution": "Use publisher_id to select existing, or create new via POST /publishers"
}
```

**Example - Unknown entity:**

```text
POST /books
{
  "title": "Some Book",
  "publisher_name": "Totally New Press"
}

Response: 400 Bad Request
{
  "error": "unknown_entity",
  "entity_type": "publisher",
  "input": "Totally New Press",
  "resolution": "Create via POST /publishers first, then reference by ID"
}
```

### Entity Creation Endpoints (`POST /publishers`, `/binders`, `/authors`)

| Scenario | Response | Action Required |
|----------|----------|-----------------|
| Exact match exists | **409 Conflict** | Use existing ID |
| Fuzzy match 80%+ | **409 Conflict** | Use existing or add `?force=true` |
| No match | **201 Created** | Normal creation |

**Example - Similar entity exists:**

```text
POST /publishers
{
  "name": "Macmillan",
  "tier": "TIER_1"
}

Response: 409 Conflict
{
  "error": "similar_entity_exists",
  "entity_type": "publisher",
  "input": "Macmillan",
  "suggestions": [
    {"id": 5, "name": "Macmillan and Co.", "tier": "TIER_1", "match": 0.95, "book_count": 12}
  ],
  "resolution": "Use existing ID, or add force=true to create anyway"
}
```

**Force creation:**

```text
POST /publishers?force=true
{
  "name": "Macmillan",
  "tier": "TIER_1"
}

Response: 201 Created
```

---

## Error Response Format

**Consistent schema for all entity validation errors:**

```python
class EntityValidationError(BaseModel):
    error: Literal["similar_entity_exists", "unknown_entity", "entity_not_found"]
    entity_type: Literal["publisher", "binder", "author"]
    input: str
    suggestions: list[EntitySuggestion] | None
    resolution: str

class EntitySuggestion(BaseModel):
    id: int
    name: str
    tier: str | None
    match: float  # 0.0-1.0
    book_count: int  # helps identify canonical entry
```

**HTTP status codes:**

| error | HTTP Code |
|-------|-----------|
| `similar_entity_exists` | 409 Conflict |
| `unknown_entity` | 400 Bad Request |
| `entity_not_found` | 404 Not Found |

---

## Fuzzy Matching Infrastructure

### New Service: `entity_matching.py`

Unified fuzzy matching for all entity types:

```python
def fuzzy_match_entity(
    db: Session,
    entity_type: Literal["publisher", "binder", "author"],
    name: str,
    threshold: float = 0.80,
    max_results: int = 5,
) -> list[EntityMatch]:
    """
    Find existing entities that fuzzy-match the given name.

    1. Apply type-specific normalization
    2. Query all entities (cached, 5-min TTL)
    3. Score with rapidfuzz token_sort_ratio
    4. Return matches above threshold, sorted by confidence
    """
```

### Normalization Rules

**All types:**

- Strip leading/trailing whitespace
- Normalize unicode (NFD → NFC)
- Collapse multiple spaces

**Publisher-specific:** (already exists)

- Strip location suffixes ("New York", "London", etc.)
- Expand abbreviations ("Wm." → "William")
- Handle dual publishers ("A / B" → "A")
- Normalize "& Co" → "& Co."

**Binder-specific:**

- Strip parenthetical descriptions: "Bayntun (of Bath)" → "Bayntun"
- Accent normalization: "Riviere" ↔ "Rivière"
- Known alias mapping (existing TIER_1/TIER_2 dicts)

**Author-specific:**

- Name order normalization: "Dickens, Charles" ↔ "Charles Dickens"
- Honorific handling: "Sir Walter Scott" ↔ "Walter Scott"
- Accent normalization: "Bronte" ↔ "Brontë"

### Caching

Extend existing publisher cache pattern to all entity types:

- In-memory cache per entity type
- 5-minute TTL
- Invalidate on create/update/delete
- Thread-safe with locking

---

## Migration Strategy

### Phase 1: Log-Only (1 week)

- Add fuzzy matching to all entity lookups
- Log warnings for would-be conflicts (don't reject)
- Monitor logs to tune threshold
- No breaking changes

**Log format:**

```text
WARN: Entity validation would reject: publisher 'Bayntun (of Bath)'
      matches 'Bayntun' at 88% (book_count: 5)
```

### Phase 2: Enforce on API

- Return 409/400 for conflicts
- Update web UI to handle suggestion responses (dropdown picker)
- Claude Code sessions will see errors and prompt user for decision

### Phase 3: Update AI Prompts

- Napoleon/extraction prompts: "Always use existing entity IDs when available"
- Provide entity lookup context before analysis
- Reduce frequency of new entity creation

---

## Affected Code Paths

| Location | Current Behavior | New Behavior |
|----------|-----------------|--------------|
| `books.py:extract_structured_data()` | Calls `get_or_create_*` | Validate first, return 409/400 |
| `worker.py` (Lambda) | Auto-creates entities | Log warning (Phase 1), fail job (Phase 2) |
| `eval_worker.py` (Lambda) | Auto-creates entities | Log warning (Phase 1), fail job (Phase 2) |
| `POST /publishers,binders,authors` | Direct creation | Validate for duplicates |
| Web UI book forms | Submits names | Handle 409 with picker UI |

---

## Configuration

**Environment variables:**

```text
ENTITY_MATCH_THRESHOLD_PUBLISHER=0.80
ENTITY_MATCH_THRESHOLD_BINDER=0.80
ENTITY_MATCH_THRESHOLD_AUTHOR=0.75  # lower due to name variations
ENTITY_VALIDATION_MODE=log  # log | enforce
```

---

## Testing Strategy

**Unit tests:**

- Normalization functions for each entity type
- Fuzzy matching with various similarity levels
- Cache invalidation

**Integration tests:**

- Book creation with similar entity names → 409
- Book creation with unknown entity names → 400
- Entity creation with similar names → 409
- Entity creation with `force=true` → 201
- ID references always succeed

**Threshold tuning tests:**

- Known duplicates from production (should match)
- Distinct entities (should not match)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| New duplicate entities created | 0 per week (down from ~5) |
| False positive rejections | <5% of legitimate new entities |
| Time to resolve 409 error | <30 seconds (clear suggestions) |

---

## Implementation Order

1. `entity_matching.py` - Unified matching service
2. Entity endpoint validation (`POST /publishers,binders,authors`)
3. Book endpoint validation (`POST/PUT /books`)
4. Phase 1 logging mode
5. Threshold tuning based on logs
6. Phase 2 enforcement
7. Web UI updates for 409 handling

---

*Design completed: 2026-01-09*
