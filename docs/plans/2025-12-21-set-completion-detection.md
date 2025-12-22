# Set Completion Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Award +25 bonus points when a new book would complete an incomplete multi-volume set in the collection.

**Architecture:** New service module `set_detection.py` with pure utility functions for parsing and a main detection function that queries the database. Integration at two call sites in `eval_generation.py` and `scoring.py`.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest, regex for parsing

**Issue:** #517

---

## Task 1: Roman Numeral Conversion Utility

**Files:**
- Create: `backend/app/services/set_detection.py`
- Create: `backend/tests/services/test_set_detection.py`

**Step 1: Create test file with Roman numeral tests**

Create `backend/tests/services/test_set_detection.py`:

```python
"""Tests for set completion detection service."""


class TestRomanToInt:
    """Tests for Roman numeral to integer conversion."""

    def test_roman_i_returns_1(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("I") == 1

    def test_roman_v_returns_5(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("V") == 5

    def test_roman_viii_returns_8(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("VIII") == 8

    def test_roman_xii_returns_12(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("XII") == 12

    def test_roman_iv_returns_4(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("IV") == 4

    def test_roman_ix_returns_9(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("IX") == 9

    def test_roman_lowercase_works(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("viii") == 8

    def test_roman_invalid_returns_none(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("INVALID") is None

    def test_roman_xiii_exceeds_limit_returns_none(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("XIII") is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.set_detection'"

**Step 3: Create service file with Roman numeral function**

Create `backend/app/services/set_detection.py`:

```python
"""Set completion detection service.

Detects when a new book would complete an incomplete multi-volume set
in the collection. Awards +25 STRATEGIC_COMPLETES_SET bonus points.

See docs/session-2025-12-21-set-completion-detection/design.md for design.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Roman numeral values (supports I-XII only)
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10}
MAX_ROMAN_VALUE = 12  # Only support volumes 1-12


def roman_to_int(s: str) -> int | None:
    """Convert Roman numeral string to integer.

    Args:
        s: Roman numeral string (case-insensitive)

    Returns:
        Integer value, or None if invalid or > 12
    """
    s = s.upper().strip()
    if not s or not all(c in "IVXLCDM" for c in s):
        return None

    result = 0
    prev_value = 0

    for char in reversed(s):
        value = ROMAN_VALUES.get(char, 0)
        if value == 0:
            return None  # Invalid Roman numeral character for our subset
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value

    if result <= 0 or result > MAX_ROMAN_VALUE:
        return None

    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestRomanToInt -v`

Expected: All 9 tests PASS

**Step 5: Commit**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git add backend/app/services/set_detection.py backend/tests/services/test_set_detection.py`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git commit -m "feat(set-detection): add Roman numeral conversion utility"`

---

## Task 2: Volume Number Extraction

**Files:**
- Modify: `backend/app/services/set_detection.py`
- Modify: `backend/tests/services/test_set_detection.py`

**Step 1: Add volume extraction tests**

Append to `backend/tests/services/test_set_detection.py`:

```python


class TestExtractVolumeNumber:
    """Tests for extracting volume number from title."""

    def test_vol_dot_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Vol. 3") == 3

    def test_vol_no_dot_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Vol 12") == 12

    def test_volume_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Complete Works Volume 2") == 2

    def test_volume_roman(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Volume VIII") == 8

    def test_vol_dot_roman(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Works Vol. IV") == 4

    def test_part_arabic(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("History Part 2") == 2

    def test_no_volume_returns_none(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Complete Works") is None

    def test_case_insensitive(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("works VOLUME viii") == 8

    def test_volume_at_end(self):
        from app.services.set_detection import extract_volume_number

        assert extract_volume_number("Byron Poetical Works, Vol. 5") == 5
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestExtractVolumeNumber -v`

Expected: FAIL with "ImportError: cannot import name 'extract_volume_number'"

**Step 3: Implement volume extraction function**

Add to `backend/app/services/set_detection.py` after `roman_to_int`:

```python


# Patterns to extract volume numbers from titles
VOLUME_PATTERNS = [
    # Vol. 3, Vol 12
    re.compile(r"\bVol\.?\s*(\d+)\b", re.IGNORECASE),
    # Volume 2, Volume VIII
    re.compile(r"\bVolume\s+(\w+)\b", re.IGNORECASE),
    # Part 1, Part 2
    re.compile(r"\bPart\s+(\d+)\b", re.IGNORECASE),
]


def extract_volume_number(title: str) -> int | None:
    """Extract volume number from a book title.

    Supports patterns:
    - Vol. 3, Vol 12
    - Volume 2, Volume VIII (Roman numerals)
    - Part 1, Part 2

    Args:
        title: Book title string

    Returns:
        Volume number as integer, or None if not found
    """
    for pattern in VOLUME_PATTERNS:
        match = pattern.search(title)
        if match:
            value = match.group(1)
            # Try as integer first
            if value.isdigit():
                return int(value)
            # Try as Roman numeral
            roman_value = roman_to_int(value)
            if roman_value is not None:
                return roman_value
    return None
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestExtractVolumeNumber -v`

Expected: All 9 tests PASS

**Step 5: Commit**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git add backend/app/services/set_detection.py backend/tests/services/test_set_detection.py`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git commit -m "feat(set-detection): add volume number extraction from titles"`

---

## Task 3: Title Normalization

**Files:**
- Modify: `backend/app/services/set_detection.py`
- Modify: `backend/tests/services/test_set_detection.py`

**Step 1: Add title normalization tests**

Append to `backend/tests/services/test_set_detection.py`:

```python


class TestNormalizeTitle:
    """Tests for stripping volume indicators from titles."""

    def test_strips_vol_dot_arabic(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Byron Works Vol. 8") == "Byron Works"

    def test_strips_vol_arabic(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works Vol 3") == "Works"

    def test_strips_volume_roman(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works, Volume III") == "Works"

    def test_strips_part(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("History Part 2") == "History"

    def test_strips_parenthetical_vols(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works (in 3 vols)") == "Works"

    def test_no_volume_unchanged(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Complete Works") == "Complete Works"

    def test_strips_trailing_whitespace(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Works Vol. 1  ") == "Works"

    def test_preserves_internal_structure(self):
        from app.services.set_detection import normalize_title

        assert normalize_title("Lord Byron's Complete Poetical Works Vol. 5") == "Lord Byron's Complete Poetical Works"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestNormalizeTitle -v`

Expected: FAIL with "ImportError: cannot import name 'normalize_title'"

**Step 3: Implement normalize_title function**

Add to `backend/app/services/set_detection.py` after `extract_volume_number`:

```python


# Patterns to strip volume indicators for title matching
NORMALIZE_PATTERNS = [
    re.compile(r"\s*,?\s*Vol\.?\s*\d+", re.IGNORECASE),  # Vol. 1, Vol 2
    re.compile(r"\s*,?\s*Volume\s+\w+", re.IGNORECASE),  # Volume III
    re.compile(r"\s*,?\s*Part\s+\d+", re.IGNORECASE),  # Part 1
    re.compile(r"\s*\([^)]*vol[^)]*\)", re.IGNORECASE),  # (in 3 vols)
]


def normalize_title(title: str) -> str:
    """Strip volume indicators from title for matching.

    Args:
        title: Full book title

    Returns:
        Title with volume indicators removed
    """
    result = title
    for pattern in NORMALIZE_PATTERNS:
        result = pattern.sub("", result)
    return result.strip()
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestNormalizeTitle -v`

Expected: All 8 tests PASS

**Step 5: Commit**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git add backend/app/services/set_detection.py backend/tests/services/test_set_detection.py`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git commit -m "feat(set-detection): add title normalization for matching"`

---

## Task 4: Title Matching

**Files:**
- Modify: `backend/app/services/set_detection.py`
- Modify: `backend/tests/services/test_set_detection.py`

**Step 1: Add title matching tests**

Append to `backend/tests/services/test_set_detection.py`:

```python


class TestTitlesMatch:
    """Tests for checking if two normalized titles represent the same work."""

    def test_exact_match(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "Byron Works") is True

    def test_case_insensitive(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "byron works") is True

    def test_subset_a_in_b(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "Byron Works Complete") is True

    def test_subset_b_in_a(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works Complete", "Byron Works") is True

    def test_no_match(self):
        from app.services.set_detection import titles_match

        assert titles_match("Byron Works", "Shelley Poems") is False

    def test_whitespace_handling(self):
        from app.services.set_detection import titles_match

        assert titles_match("  Byron Works  ", "Byron Works") is True
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestTitlesMatch -v`

Expected: FAIL with "ImportError: cannot import name 'titles_match'"

**Step 3: Implement titles_match function**

Add to `backend/app/services/set_detection.py` after `normalize_title`:

```python


def titles_match(title_a: str, title_b: str) -> bool:
    """Check if two normalized titles represent the same work.

    Uses exact match or substring containment (for variant titles).

    Args:
        title_a: First normalized title
        title_b: Second normalized title

    Returns:
        True if titles match
    """
    a = title_a.lower().strip()
    b = title_b.lower().strip()

    if a == b:
        return True
    if a in b or b in a:
        return True

    return False
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestTitlesMatch -v`

Expected: All 6 tests PASS

**Step 5: Commit**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git add backend/app/services/set_detection.py backend/tests/services/test_set_detection.py`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git commit -m "feat(set-detection): add title matching function"`

---

## Task 5: Main Detection Function with Integration Tests

**Files:**
- Modify: `backend/app/services/set_detection.py`
- Modify: `backend/tests/services/test_set_detection.py`

**Step 1: Add integration tests for detect_set_completion**

Append to `backend/tests/services/test_set_detection.py`:

```python

from app.models.author import Author
from app.models.book import Book


class TestDetectSetCompletion:
    """Integration tests for set completion detection."""

    def test_completes_set_true(self, db):
        """Vol 3 completes set when Vols 1, 2, 4 already owned."""
        from app.services.set_detection import detect_set_completion

        # Setup: Create author with Vols 1, 2, 4 of 4-volume set
        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        for vol in [1, 2, 4]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
        db.commit()

        # Test: Vol 3 completes the set
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is True

    def test_completes_set_false_not_final(self, db):
        """Vol 3 does NOT complete when only Vols 1, 2 owned (missing 4)."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        for vol in [1, 2]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
        db.commit()

        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False

    def test_completes_set_false_no_matches(self, db):
        """Returns False when no matching books in collection."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False

    def test_completes_set_false_multivolume_record(self, db):
        """Skip detection for multi-volume set as single record."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        # This is a complete 4-volume set, not a single volume
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Complete Works",  # No volume indicator
            volumes=4,  # Multi-volume set
        )
        assert result is False

    def test_excludes_book_id(self, db):
        """Excludes specified book from matching."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        books = []
        for vol in [1, 2, 3, 4]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
            books.append(book)
        db.commit()

        # When checking existing book Vol 3, exclude it - still need to own 3 others
        # With 4 volumes total and excluding Vol 3, we have 3 others
        # 3 + 1 = 4 = set size, so it WOULD complete (if we didn't already have it)
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
            book_id=books[2].id,  # Exclude Vol 3
        )
        # With Vol 3 excluded, we have Vols 1, 2, 4 - adding Vol 3 completes
        assert result is True

    def test_roman_numeral_volumes(self, db):
        """Handles Roman numeral volume indicators."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        for vol in ["I", "II", "IV"]:
            book = Book(
                title=f"Works Volume {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)
        db.commit()

        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Volume III",
            volumes=1,
        )
        assert result is True

    def test_excludes_removed_books(self, db):
        """Excludes books with REMOVED status."""
        from app.services.set_detection import detect_set_completion

        author = Author(name="Lord Byron")
        db.add(author)
        db.commit()

        # Add Vols 1, 2 as OWNED
        for vol in [1, 2]:
            book = Book(
                title=f"Works Vol. {vol}",
                author_id=author.id,
                volumes=4,
                status="OWNED",
            )
            db.add(book)

        # Add Vol 4 as REMOVED - should not count
        removed = Book(
            title="Works Vol. 4",
            author_id=author.id,
            volumes=4,
            status="REMOVED",
        )
        db.add(removed)
        db.commit()

        # Only have Vols 1, 2 (OWNED), adding Vol 3 doesn't complete
        result = detect_set_completion(
            db=db,
            author_id=author.id,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False

    def test_no_author_id_returns_false(self, db):
        """Returns False when author_id is None."""
        from app.services.set_detection import detect_set_completion

        result = detect_set_completion(
            db=db,
            author_id=None,
            title="Works Vol. 3",
            volumes=1,
        )
        assert result is False
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestDetectSetCompletion -v`

Expected: FAIL with "ImportError: cannot import name 'detect_set_completion'"

**Step 3: Implement detect_set_completion function**

Add to `backend/app/services/set_detection.py` after `titles_match`:

```python

from sqlalchemy.orm import Session

from app.models.book import Book


def find_set_members(
    db: Session,
    author_id: int,
    normalized_title: str,
    exclude_book_id: int | None = None,
) -> list[Book]:
    """Find books that belong to the same set.

    Args:
        db: Database session
        author_id: Author ID to match
        normalized_title: Title with volume indicators stripped
        exclude_book_id: Book ID to exclude from results

    Returns:
        List of matching books
    """
    query = db.query(Book).filter(
        Book.author_id == author_id,
        Book.status != "REMOVED",
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


def detect_set_completion(
    db: Session,
    author_id: int | None,
    title: str,
    volumes: int,
    book_id: int | None = None,
) -> bool:
    """Detect if this book would complete an incomplete set.

    Args:
        db: Database session
        author_id: Author of the book
        title: Full title (may include volume indicator)
        volumes: Number of volumes (1 = single volume)
        book_id: Exclude this book from matching (for existing books)

    Returns:
        True if acquiring this book completes a set
    """
    try:
        # Guard: need author to match
        if not author_id:
            return False

        # Extract volume from this book's title
        this_volume = extract_volume_number(title)

        # If no volume indicator and volumes > 1, this is a complete set record
        if this_volume is None and volumes > 1:
            return False

        # If no volume indicator and volumes == 1, single-volume work
        if this_volume is None:
            return False

        # Normalize title for matching
        normalized = normalize_title(title)

        # Find matching books in collection
        matches = find_set_members(db, author_id, normalized, book_id)

        if not matches:
            return False

        # Determine set size from max volumes field
        set_size = max(book.volumes or 1 for book in matches)

        # If set size is 1, not a multi-volume set
        if set_size <= 1:
            return False

        # Collect owned volume numbers
        owned_volumes = set()
        for book in matches:
            vol = extract_volume_number(book.title)
            if vol is not None:
                owned_volumes.add(vol)

        # Check if adding this volume completes the set
        # owned + 1 (this book) == set_size
        if len(owned_volumes) + 1 == set_size:
            return True

        return False

    except Exception as e:
        logger.warning(f"Set detection failed: {e}")
        return False  # Fail-safe: don't break scoring
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py::TestDetectSetCompletion -v`

Expected: All 8 tests PASS

**Step 5: Run all tests to verify no regressions**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/services/test_set_detection.py -v`

Expected: All 40 tests PASS (9 + 9 + 8 + 6 + 8)

**Step 6: Run lint**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run ruff check app/services/set_detection.py tests/services/test_set_detection.py`

Expected: No errors

**Step 7: Commit**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git add backend/app/services/set_detection.py backend/tests/services/test_set_detection.py`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git commit -m "feat(set-detection): add main detection function with DB integration"`

---

## Task 6: Integrate into eval_generation.py

**Files:**
- Modify: `backend/app/services/eval_generation.py:555`

**Step 1: Read current context around line 555**

Verify the exact location and surrounding code.

**Step 2: Add import at top of file**

Add to imports section of `backend/app/services/eval_generation.py`:

```python
from app.services.set_detection import detect_set_completion
```

**Step 3: Replace hardcoded False with detection call**

In `backend/app/services/eval_generation.py` at line 555, replace:

```python
        completes_set=False,  # TODO: Implement set completion detection
```

with:

```python
        completes_set=detect_set_completion(
            db=db,
            author_id=book.author_id,
            title=book.title,
            volumes=book.volumes or 1,
            book_id=book.id,
        ),
```

**Step 4: Run existing tests to verify no regressions**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/ -q`

Expected: All tests PASS

**Step 5: Run lint**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run ruff check app/services/eval_generation.py`

Expected: No errors

**Step 6: Commit**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git add backend/app/services/eval_generation.py`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git commit -m "feat(set-detection): integrate into eval_generation scoring"`

---

## Task 7: Integrate into scoring.py

**Files:**
- Modify: `backend/app/services/scoring.py:628`

**Step 1: Read current context around line 628**

Verify the exact location and surrounding code.

**Step 2: Add import at top of file**

Add to imports section of `backend/app/services/scoring.py`:

```python
from app.services.set_detection import detect_set_completion
```

**Step 3: Replace hardcoded False with detection call**

In `backend/app/services/scoring.py` at line 628, replace:

```python
        completes_set=False,
```

with:

```python
        completes_set=detect_set_completion(
            db=db,
            author_id=book.author_id,
            title=book.title,
            volumes=book.volumes or 1,
            book_id=book.id,
        ),
```

**Step 4: Run existing tests to verify no regressions**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest tests/ -q`

Expected: All tests PASS

**Step 5: Run lint**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run ruff check app/services/scoring.py`

Expected: No errors

**Step 6: Commit**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git add backend/app/services/scoring.py`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git commit -m "feat(set-detection): integrate into scoring.py"`

---

## Task 8: Final Verification and PR

**Step 1: Run full test suite**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run pytest -q`

Expected: All tests PASS (including new set_detection tests)

**Step 2: Run full lint**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run ruff check .`

Expected: No errors

**Step 3: Run format check**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion/backend && poetry run ruff format --check .`

Expected: No files would be reformatted

**Step 4: Push branch**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && git push -u origin feat/set-completion-517`

**Step 5: Create PR**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-set-completion && gh pr create --base staging --title "feat: Set completion detection (#517)" --body "## Summary
- Adds set_detection.py service module
- Detects when new book completes multi-volume set
- Awards +25 STRATEGIC_COMPLETES_SET bonus points
- Integrates into eval_generation.py and scoring.py

## Test Plan
- [x] Unit tests for Roman numeral conversion
- [x] Unit tests for volume extraction
- [x] Unit tests for title normalization
- [x] Unit tests for title matching
- [x] Integration tests for detection logic
- [ ] CI passes

Closes #517"`

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Roman numeral conversion | 9 |
| 2 | Volume number extraction | 9 |
| 3 | Title normalization | 8 |
| 4 | Title matching | 6 |
| 5 | Main detection function | 8 |
| 6 | Integrate eval_generation.py | - |
| 7 | Integrate scoring.py | - |
| 8 | Final verification + PR | - |

**Total new tests:** 40

**Files created:**
- `backend/app/services/set_detection.py`
- `backend/tests/services/test_set_detection.py`

**Files modified:**
- `backend/app/services/eval_generation.py`
- `backend/app/services/scoring.py`
