"""Set completion detection service.

Detects when a new book would complete an incomplete multi-volume set
in the collection. Awards +25 STRATEGIC_COMPLETES_SET bonus points.

See docs/session-2025-12-21-set-completion-detection/design.md for design.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.models.book import Book

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


# Patterns to extract volume numbers from titles
VOLUME_PATTERNS = [
    # Vol. 3, Vol 12, Vol. IV (both digits and roman)
    re.compile(r"\bVol\.?\s*(\w+)\b", re.IGNORECASE),
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
