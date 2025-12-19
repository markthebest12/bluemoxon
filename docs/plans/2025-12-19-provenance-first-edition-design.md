# Issue #466: Provenance and First Edition Searchable Fields

## Status: DEPLOYED TO STAGING (Infrastructure Complete)
**Pending:** Napoleon prompt not outputting structured metadata - needs debugging

## Summary

Add structured, searchable boolean/tier fields for provenance and first edition status that:
1. Are filterable in the UI
2. Get auto-populated by AI during analysis
3. Factor into valuation considerations

## New Database Fields

| Field | Type | Default | Indexed | Description |
|-------|------|---------|---------|-------------|
| `is_first_edition` | `BOOLEAN` | `NULL` | Yes | `true`/`false`/`null` (unknown) |
| `has_provenance` | `BOOLEAN` | `FALSE` | Yes | Whether book has any provenance |
| `provenance_tier` | `VARCHAR(20)` | `NULL` | Yes | `"Tier 1"`, `"Tier 2"`, `"Tier 3"`, or `NULL` |

## Provenance Tier Definitions

- **Tier 1:** Famous figures (royalty, presidents, major authors, celebrities, major institutions)
- **Tier 2:** Notable in field (known collectors, scholars, regional libraries)
- **Tier 3:** Documented but ordinary (bookplates from unknown persons, generic stamps)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ANALYSIS FLOW                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. User triggers analysis                                               │
│           ↓                                                              │
│  2. worker.py calls Bedrock/Claude with Napoleon prompt                  │
│           ↓                                                              │
│  3. Napoleon returns analysis with METADATA block:                       │
│      <!-- METADATA_START -->                                             │
│      {"is_first_edition": true, "has_provenance": true,                  │
│       "provenance_tier": "Tier 1"}                                       │
│      <!-- METADATA_END -->                                               │
│           ↓                                                              │
│  4. analysis_parser.py extracts metadata via regex                       │
│           ↓                                                              │
│  5. apply_metadata_to_book() updates Book model                          │
│           ↓                                                              │
│  6. Fields visible in API response, filterable in UI                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Database Migration
**File:** `backend/alembic/versions/q0123456cdef_add_provenance_first_edition.py`

```python
def upgrade():
    op.add_column('books', sa.Column('is_first_edition', sa.Boolean(), nullable=True))
    op.add_column('books', sa.Column('has_provenance', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('books', sa.Column('provenance_tier', sa.String(20), nullable=True))
    op.create_index('books_is_first_edition_idx', 'books', ['is_first_edition'])
    op.create_index('books_has_provenance_idx', 'books', ['has_provenance'])
    op.create_index('books_provenance_tier_idx', 'books', ['provenance_tier'])
```

**Note:** Migration also added to `backend/app/api/v1/health.py` for `/health/migrate` endpoint (idempotent SQL for Lambda deployment).

### 2. Book Model
**File:** `backend/app/models/book.py` (lines 120-123)

```python
# Searchable provenance/edition fields (auto-populated by analysis)
is_first_edition: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
has_provenance: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
provenance_tier: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
```

### 3. Pydantic Schemas
**File:** `backend/app/schemas/book.py`

**BookBase** (lines 38-40):
```python
is_first_edition: bool | None = None
has_provenance: bool = False
provenance_tier: str | None = None
```

**BookUpdate** (lines 104-106):
```python
is_first_edition: bool | None = None
has_provenance: bool | None = None
provenance_tier: str | None = None
```

**BookResponse** inherits from BookBase (line 158 comment confirms).

### 4. API Filters
**File:** `backend/app/api/v1/books.py` (lines 252-254, 326-335)

Query parameters:
```python
has_provenance: bool | None = None,
provenance_tier: str | None = None,
is_first_edition: bool | None = None,
```

Filter logic:
```python
if has_provenance is not None:
    query = query.filter(Book.has_provenance == has_provenance)
if provenance_tier:
    query = query.filter(Book.provenance_tier == provenance_tier)
if is_first_edition is not None:
    query = query.filter(Book.is_first_edition == is_first_edition)
```

### 5. Analysis Metadata Parser
**File:** `backend/app/services/analysis_parser.py`

```python
def extract_analysis_metadata(analysis_text: str) -> dict | None:
    """Extract structured metadata block from analysis response.

    Looks for JSON between <!-- METADATA_START --> and <!-- METADATA_END --> markers.
    """
    pattern = r"<!-- METADATA_START -->\s*(\{.*?\})\s*<!-- METADATA_END -->"
    match = re.search(pattern, analysis_text, re.DOTALL)
    # ... parse JSON and return dict or None

def apply_metadata_to_book(book, metadata: dict) -> list[str]:
    """Apply extracted metadata to book model.

    Data integrity rules:
    - If has_provenance becomes False, clear provenance_tier
    - Only set provenance_tier if has_provenance is True
    """
```

### 6. Worker Integration
**File:** `backend/app/worker.py` (lines 14, 216-223)

```python
from app.services.analysis_parser import apply_metadata_to_book, extract_analysis_metadata

# After analysis is saved:
metadata = extract_analysis_metadata(analysis_text)
if metadata:
    updated_fields = apply_metadata_to_book(book, metadata)
    if updated_fields:
        logger.info(f"Applied analysis metadata to book {book_id}: {', '.join(updated_fields)}")
```

### 7. Napoleon Prompt Update
**Location:** S3 bucket (bluemoxon-prompts-{env}/napoleon/v2/prompt.md)

**Required addition to prompt:**
```markdown
## Structured Metadata Output

At the END of your analysis, include a metadata block with the following format:

<!-- METADATA_START -->
{
  "is_first_edition": true,
  "has_provenance": true,
  "provenance_tier": "Tier 1"
}
<!-- METADATA_END -->

Field definitions:
- is_first_edition: true if confirmed first edition, false if later edition, null if uncertain
- has_provenance: true if any provenance indicators exist (bookplates, inscriptions, stamps, ownership marks)
- provenance_tier:
  - "Tier 1": Famous figures (royalty, presidents, major authors, celebrities, institutions)
  - "Tier 2": Notable in field (known collectors, scholars, regional libraries)
  - "Tier 3": Documented but ordinary (unknown persons, generic stamps)
  - null: No provenance or tier uncertain
```

**CURRENT ISSUE:** The Napoleon prompt may not have this section, or Claude is not outputting the metadata block. This needs debugging.

### 8. Frontend Types
**File:** `frontend/src/stores/books.ts`

Book interface:
```typescript
is_first_edition: boolean | null
has_provenance: boolean
provenance_tier: string | null
```

Filters interface:
```typescript
provenance_tier: string | null
is_first_edition: boolean | null
```

### 9. Frontend Badges (BookDetailView)
**File:** `frontend/src/views/BookDetailView.vue`

Displays badges for:
- First Edition (green badge if `is_first_edition === true`)
- Provenance tier (colored badge based on tier level)

### 10. Frontend Filters (BooksView)
**File:** `frontend/src/views/BooksView.vue`

Filter dropdowns:
- "First Edition" - Yes/No/Any
- "Provenance Tier" - Tier 1/Tier 2/Tier 3/Any

### 11. Frontend Edit Form (BookForm)
**File:** `frontend/src/components/books/BookForm.vue`

Manual editing fields:
- First Edition checkbox (tri-state: Yes/No/Unknown)
- Has Provenance checkbox
- Provenance Tier dropdown (only enabled when has_provenance is true)

---

## Test Coverage

**File:** `backend/tests/test_analysis_parser.py` - 19 tests

### Extraction Tests:
- `test_extract_valid_metadata` - Valid JSON extraction
- `test_extract_no_markers` - No metadata markers present
- `test_extract_invalid_json` - Malformed JSON handling
- `test_extract_null_values` - Null value handling
- `test_extract_multiline_json` - Multiline JSON formatting
- `test_extract_whitespace_tolerance` - Whitespace between markers

### Application Tests:
- `test_apply_first_edition_true/false/null` - First edition values
- `test_apply_provenance_with_tier` - Provenance + tier together
- `test_apply_provenance_tier_requires_has_provenance` - Data integrity
- `test_clear_tier_when_has_provenance_becomes_false` - Tier clearing
- `test_apply_tier_when_book_already_has_provenance` - Existing provenance
- `test_apply_all_fields` - All fields together
- `test_apply_empty_metadata` - Empty metadata dict
- `test_apply_only_first_edition/has_provenance` - Single field updates
- `test_tier_values` - All tier value variants
- `test_clearing_tier_explicitly_with_null` - Explicit null tier

---

## API Usage

### Filter by first edition:
```bash
bmx-api GET "/books?is_first_edition=true"
bmx-api GET "/books?is_first_edition=false"
```

### Filter by provenance:
```bash
bmx-api GET "/books?has_provenance=true"
bmx-api GET "/books?provenance_tier=Tier%201"
```

### Combined filters:
```bash
bmx-api GET "/books?is_first_edition=true&has_provenance=true&provenance_tier=Tier%201"
```

### Response includes new fields:
```json
{
  "id": 123,
  "title": "Example Book",
  "is_first_edition": true,
  "has_provenance": true,
  "provenance_tier": "Tier 1",
  ...
}
```

---

## Current State & Next Steps

### ALTERNATIVE APPROACH: Two-Stage Extraction

Instead of trying to get Napoleon to output structured data inline (unreliable), use a **second focused Bedrock call** after analysis completes:

**See:** `docs/plans/2025-12-19-two-stage-extraction.md`

**Architecture:**
1. Stage 1: Napoleon generates analysis (unchanged)
2. Stage 2: Focused extraction prompt takes analysis text → outputs JSON

**Benefits:**
- Decouples analysis quality from data extraction
- Simple extraction prompt is much harder for AI to ignore
- Falls back gracefully if extraction fails

**This is the recommended path forward** if Napoleon continues to ignore inline metadata instructions.

---

### COMPLETED:
1. Database migration (deployed to staging)
2. Book model with new fields
3. Pydantic schemas
4. API filters working
5. Analysis parser service
6. Worker integration (calls parser after analysis)
7. 19 backend tests (all passing)
8. Frontend types updated
9. Frontend badges in BookDetailView
10. Frontend filters in BooksView
11. Frontend edit form in BookForm
12. All CI checks passing
13. Deployed to staging

### PENDING - Napoleon Prompt Issue:
The structured metadata is not appearing in analysis output. Debug steps:

1. **Check Napoleon prompt in S3:**
   ```bash
   # Find correct bucket name
   AWS_PROFILE=bmx-staging aws s3 ls | grep prompt

   # Download and inspect prompt
   AWS_PROFILE=bmx-staging aws s3 cp s3://BUCKET_NAME/napoleon/v2/prompt.md .tmp/prompt.md
   cat .tmp/prompt.md | grep -A 20 "METADATA"
   ```

2. **Verify prompt has metadata instructions** - The prompt must include:
   - The `<!-- METADATA_START -->` and `<!-- METADATA_END -->` markers
   - JSON schema with `is_first_edition`, `has_provenance`, `provenance_tier`
   - Clear instructions to output this at the END of analysis

3. **If prompt is missing metadata section:**
   - Download current prompt
   - Add metadata section (see section 7 above)
   - Upload updated prompt:
     ```bash
     AWS_PROFILE=bmx-staging aws s3 cp .tmp/prompt.md s3://BUCKET_NAME/napoleon/v2/prompt.md
     ```

4. **Test with a fresh analysis:**
   - Pick a book without analysis
   - Trigger analysis via UI or API
   - Check Lambda logs for "Applied analysis metadata" message
   - Verify book record has new field values

5. **If Claude is ignoring instructions:**
   - Make metadata section more prominent in prompt
   - Add examples of expected output
   - Consider moving to start of prompt or adding emphasis

---

## Files Modified (Complete List)

### Backend:
- `backend/alembic/versions/q0123456cdef_add_provenance_first_edition.py` - Migration
- `backend/app/models/book.py` - Model fields
- `backend/app/schemas/book.py` - Pydantic schemas
- `backend/app/api/v1/books.py` - API filters
- `backend/app/api/v1/health.py` - Idempotent migration SQL
- `backend/app/services/analysis_parser.py` - NEW: Metadata extraction
- `backend/app/worker.py` - Worker integration
- `backend/tests/test_analysis_parser.py` - NEW: 19 tests

### Frontend:
- `frontend/src/stores/books.ts` - Types
- `frontend/src/views/BookDetailView.vue` - Badges
- `frontend/src/views/BooksView.vue` - Filters
- `frontend/src/components/books/BookForm.vue` - Edit form

### Infrastructure:
- Napoleon prompt in S3 (needs update/verification)

---

## PR History

- **PR #467** - Merged to staging (all infrastructure)
- **Deploy** - Workflow run 20371798771 completed successfully
- **Smoke tests** - All passing

---

## Regex Pattern Reference

The parser uses this regex to find metadata:
```python
pattern = r"<!-- METADATA_START -->\s*(\{.*?\})\s*<!-- METADATA_END -->"
```

This matches:
- Literal `<!-- METADATA_START -->`
- Any whitespace
- JSON object (non-greedy capture)
- Any whitespace
- Literal `<!-- METADATA_END -->`

The `re.DOTALL` flag allows `.` to match newlines for multiline JSON.
