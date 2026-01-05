# Set Completion Detection - Design Document

**Issue:** #517
**Date:** 2025-12-21
**Status:** Design Complete - Ready for Implementation

---

## Design Decisions (from Brainstorming)

| Question | Decision |
|----------|----------|
| Scope | **Cross-book matching** - detect when new book completes set by matching OTHER books in collection |
| Matching strategy | **Author + Normalized Title** - simple, matches collector mental model |
| Volume extraction | **Title parsing + volumes field** - handles both explicit volumes and multi-volume sets |
| Set size determination | **Max volumes field** - use highest `volumes` value from matched books |
| Matching strictness | **Author + Title only** - ignore publisher/edition differences |

---

## Algorithm Overview

When evaluating a new book for acquisition, determine if it would complete an incomplete set in the collection.

**Inputs:**
- New book being evaluated (author, title, volumes field)
- Existing collection (database query)

**Algorithm Steps:**

1. **Extract volume info from new book's title**
   - Parse for patterns: "Vol. 1", "Volume I", "Part 2", etc.
   - If found: this is a single volume (volume_number = extracted)
   - If not found and `volumes > 1`: this is a complete multi-volume set (skip detection)
   - If not found and `volumes == 1`: single-volume work (skip detection)

2. **Normalize the title**
   - Strip volume indicators from title
   - "Byron Complete Works Vol. VIII" → "Byron Complete Works"

3. **Find matching books in collection**
   - Query: same author + normalized title match
   - Exclude the book itself if already in DB

4. **Determine set size and owned volumes**
   - Set size = max(`volumes`) across all matched books
   - Owned volumes = set of extracted volume numbers from matched books

5. **Check completion**
   - If `len(owned_volumes) + 1 == set_size`: return `True`
   - Otherwise: return `False`

**Output:** `completes_set: bool`

---

## Volume Parsing Patterns

**Supported Formats (case-insensitive):**

| Pattern | Examples | Extracted |
|---------|----------|-----------|
| `Vol. N` | "Vol. 1", "Vol. 8" | 1, 8 |
| `Vol N` | "Vol 3", "Vol 12" | 3, 12 |
| `Volume N` | "Volume 2" | 2 |
| `Volume Roman` | "Volume III", "Volume VIII" | 3, 8 |
| `Vol. Roman` | "Vol. IV", "Vol. XI" | 4, 11 |
| `Part N` | "Part 1", "Part 2" | 1, 2 |

**Roman Numeral Support:** I-XII (1-12)

**Title Normalization:**

```python
def normalize_title(title: str) -> str:
    """Strip volume indicators for matching."""
    patterns = [
        r'\s*,?\s*Vol\.?\s*\d+',      # Vol. 1, Vol 2
        r'\s*,?\s*Volume\s+\w+',       # Volume III
        r'\s*,?\s*Part\s+\d+',         # Part 1
        r'\s*\([^)]*vol[^)]*\)',       # (in 3 vols)
    ]
    result = title
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    return result.strip()
```

---

## Database Query & Matching

**Finding Matching Books:**

```python
def find_set_members(
    db: Session,
    author_id: int,
    normalized_title: str,
    exclude_book_id: int | None = None
) -> list[Book]:
    """Find books that belong to the same set."""
    query = db.query(Book).filter(
        Book.author_id == author_id,
        Book.status != "REMOVED"
    )

    if exclude_book_id:
        query = query.filter(Book.id != exclude_book_id)

    candidates = query.all()

    matches = []
    for book in candidates:
        book_normalized = normalize_title(book.title)
        if titles_match(normalized_title, book_normalized):
            matches.append(book)

    return matches
```

**Title Matching:**

```python
def titles_match(title_a: str, title_b: str) -> bool:
    """Check if two normalized titles represent the same work."""
    a = title_a.lower().strip()
    b = title_b.lower().strip()

    if a == b:
        return True
    if a in b or b in a:
        return True

    return False
```

---

## Integration Points

**New file:** `backend/app/services/set_detection.py`

**Caller 1: `eval_generation.py:555`**

```python
# Current
completes_set=False,  # TODO: Implement set completion detection

# After
from app.services.set_detection import detect_set_completion

completes_set = detect_set_completion(
    db=db,
    author_id=book.author_id,
    title=book.title,
    volumes=book.volumes,
    book_id=book.id,
)
```

**Caller 2: `scoring.py:628`**

```python
# Current
completes_set=False,

# After
completes_set = detect_set_completion(
    db=db,
    author_id=book.author_id,
    title=book.title,
    volumes=book.volumes,
    book_id=book.id,
)
```

**Function Signature:**

```python
def detect_set_completion(
    db: Session,
    author_id: int,
    title: str,
    volumes: int,
    book_id: int | None = None,
) -> bool:
    """
    Detect if this book would complete an incomplete set.

    Args:
        db: Database session
        author_id: Author of the book
        title: Full title (may include volume indicator)
        volumes: Number of volumes (1 = single volume)
        book_id: Exclude this book from matching (for existing books)

    Returns:
        True if acquiring this book completes a set
    """
```

---

## Testing Strategy

**Test File:** `backend/tests/services/test_set_detection.py`

**Unit Tests:**

```python
# Volume extraction
def test_extract_volume_arabic():
    assert extract_volume_number("Works Vol. 3") == 3

def test_extract_volume_roman():
    assert extract_volume_number("Works Volume VIII") == 8

def test_extract_volume_none():
    assert extract_volume_number("Complete Works") is None

# Title normalization
def test_normalize_title():
    assert normalize_title("Byron Works Vol. 8") == "Byron Works"
    assert normalize_title("Works, Volume III") == "Works"

# Title matching
def test_titles_match_exact():
    assert titles_match("Byron Works", "Byron Works") is True

def test_titles_match_subset():
    assert titles_match("Byron Works", "Byron Works Complete") is True
```

**Integration Tests:**

```python
def test_completes_set_true(db_session):
    # Setup: Create author with Vols 1, 2, 4 of 4-volume set
    author = create_author(db_session, "Byron")
    create_book(db_session, author, "Works Vol. 1", volumes=4)
    create_book(db_session, author, "Works Vol. 2", volumes=4)
    create_book(db_session, author, "Works Vol. 4", volumes=4)

    # Test: Vol 3 completes the set
    result = detect_set_completion(
        db=db_session,
        author_id=author.id,
        title="Works Vol. 3",
        volumes=1,
    )
    assert result is True

def test_completes_set_false_not_final(db_session):
    # Setup: Vols 1, 2 of 4-volume set
    # Test: Vol 3 does NOT complete (still missing Vol 4)
    ...
```

---

## Edge Cases & Error Handling

| Case | Behavior |
|------|----------|
| No author_id | Return `False` |
| Multi-volume set as single record | Skip detection (`volumes > 1` with no volume in title) |
| No matching books found | Return `False` |
| Only one volume in collection | Return `False` |
| Roman numeral > XII | Return `False` |
| Duplicate volume numbers | Use set() to deduplicate |

**Fail-safe Error Handling:**

```python
def detect_set_completion(...) -> bool:
    try:
        # ... detection logic ...
    except Exception as e:
        logger.warning(f"Set detection failed: {e}")
        return False  # Fail-safe: don't break scoring
```

---

## Implementation Phases

1. **Phase 1: Volume Extraction Utility**
   - `extract_volume_number(title: str) -> int | None`
   - `normalize_title(title: str) -> str`
   - Roman numeral conversion
   - Unit tests

2. **Phase 2: Set Detection Service**
   - `detect_set_completion()` function
   - `find_set_members()` query
   - `titles_match()` comparison
   - Integration tests

3. **Phase 3: Integration**
   - Update `eval_generation.py:555`
   - Update `scoring.py:628`
   - End-to-end verification

---

## Next Steps

Use Superpowers skill chain to implement:

```
using-git-worktrees → writing-plans → subagent-driven-development
```

1. Create isolated worktree for feature branch
2. Write detailed implementation plan with tasks
3. Execute tasks with code review between each

---

*Design completed: 2025-12-21*
