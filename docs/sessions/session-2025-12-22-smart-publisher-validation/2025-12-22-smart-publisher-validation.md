# Smart Publisher Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a validation layer that normalizes publisher names before database save, using rules-based auto-correction, fuzzy matching to existing entries, and AI inference for canonical names.

**Architecture:** A publisher validation service that sits between analysis extraction and database save. It auto-corrects common issues (location suffixes, dual publishers), fuzzy-matches against existing publishers with confidence scoring, and uses AI to infer canonical names for new/unknown publishers. High confidence matches auto-accept, medium require confirmation, low flag for review, and new publishers are created minimally then queued for enrichment.

**Tech Stack:** Python 3.12, SQLAlchemy, FastAPI, pytest, Levenshtein distance (rapidfuzz library), Claude Bedrock for AI inference.

**Session Log:** `docs/session-2025-12-22-smart-publisher-validation/`

**CRITICAL Bash Rules:**

- NEVER use `#`, `\`, `$(...)`, `&&`, `||`, or `!` in commands
- Use simple single-line commands only
- Use separate sequential Bash tool calls instead of chaining

---

## Phase 1: Publisher Normalization Service (Foundation)

### Task 1: Add rapidfuzz dependency

**Files:**

- Modify: `backend/pyproject.toml`

**Step 1: Add rapidfuzz to dependencies**

Add to `[tool.poetry.dependencies]` section:

```toml
rapidfuzz = "^3.10.0"
```

**Step 2: Install dependency**

Run: `cd backend && poetry add rapidfuzz`

**Step 3: Verify installation**

Run: `cd backend && poetry run python -c "from rapidfuzz import fuzz; print(fuzz.ratio('test', 'test'))"`
Expected: `100.0`

**Step 4: Commit**

Run: `git add backend/pyproject.toml backend/poetry.lock`
Run: `git commit -m "chore: add rapidfuzz for fuzzy string matching"`

---

### Task 2: Write failing tests for publisher auto-correct rules

**Files:**

- Create: `backend/tests/test_publisher_validation.py`

**Step 1: Write the failing tests**

```python
"""Tests for publisher validation service."""

import pytest

from app.services.publisher_validation import auto_correct_publisher_name


class TestAutoCorrectPublisherName:
    """Test auto-correction rules for publisher names."""

    def test_removes_new_york_suffix(self):
        result = auto_correct_publisher_name("Harper & Brothers, New York")
        assert result == "Harper & Brothers"

    def test_removes_london_suffix(self):
        result = auto_correct_publisher_name("Macmillan and Co., London")
        assert result == "Macmillan and Co."

    def test_removes_philadelphia_suffix(self):
        result = auto_correct_publisher_name("J.B. Lippincott Company, Philadelphia")
        assert result == "J.B. Lippincott Company"

    def test_removes_boston_suffix(self):
        result = auto_correct_publisher_name("D.C. Heath & Co., Boston")
        assert result == "D.C. Heath & Co."

    def test_removes_parenthetical_edition_info(self):
        result = auto_correct_publisher_name("D.C. Heath & Co. (Arden Shakespeare)")
        assert result == "D.C. Heath & Co."

    def test_removes_parenthetical_series_info(self):
        result = auto_correct_publisher_name("Oxford University Press (World's Classics)")
        assert result == "Oxford University Press"

    def test_handles_dual_publisher_keeps_first(self):
        result = auto_correct_publisher_name("Doubleday, Page & Company / Review of Reviews")
        assert result == "Doubleday, Page & Company"

    def test_handles_dual_publisher_with_ampersand(self):
        result = auto_correct_publisher_name("Henry Frowde / Oxford University Press")
        assert result == "Oxford University Press"

    def test_expands_d_to_david_for_bogue(self):
        result = auto_correct_publisher_name("D. Bogue")
        assert result == "David Bogue"

    def test_normalizes_ampersand_co_punctuation(self):
        result = auto_correct_publisher_name("Harper & Co")
        assert result == "Harper & Co."

    def test_preserves_clean_name(self):
        result = auto_correct_publisher_name("Oxford University Press")
        assert result == "Oxford University Press"

    def test_handles_multiple_issues(self):
        result = auto_correct_publisher_name("D. Bogue, Fleet-Street (First Edition)")
        assert result == "David Bogue"

    def test_strips_whitespace(self):
        result = auto_correct_publisher_name("  Harper & Brothers  ")
        assert result == "Harper & Brothers"
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.publisher_validation'"

**Step 3: Commit failing tests**

Run: `git add backend/tests/test_publisher_validation.py`
Run: `git commit -m "test: add failing tests for publisher auto-correct rules"`

---

### Task 3: Implement auto_correct_publisher_name function

**Files:**

- Create: `backend/app/services/publisher_validation.py`

**Step 1: Write minimal implementation**

```python
"""Publisher validation service for normalizing and matching publisher names."""

import re

# Location suffixes to remove (case-insensitive)
LOCATION_SUFFIXES = [
    r",?\s+New York\s*$",
    r",?\s+London\s*$",
    r",?\s+Philadelphia\s*$",
    r",?\s+Boston\s*$",
    r",?\s+Chicago\s*$",
    r",?\s+Edinburgh\s*$",
    r",?\s+Leipzig\s*$",
    r",?\s+Wien\s*$",
    r",?\s+Fleet-Street\s*$",
    r",?\s+St\.?\s*Paul\s*$",
    r",?\s+Keene\s+NH\s*$",
    r",?\s+San Francisco\s*$",
]

# Known abbreviation expansions
ABBREVIATION_EXPANSIONS = {
    "D. Bogue": "David Bogue",
    "Wm.": "William",
    "Chas.": "Charles",
    "Thos.": "Thomas",
    "Jas.": "James",
    "Jno.": "John",
}

# Dual publisher patterns - which to keep
# Format: (pattern, replacement) - replacement can reference groups
DUAL_PUBLISHER_RULES = [
    # Keep Oxford University Press over Henry Frowde
    (r"Henry Frowde\s*/\s*Oxford University Press", "Oxford University Press"),
    # Keep Humphrey Milford variant -> Oxford University Press
    (r"Oxford University Press\s*/\s*Humphrey Milford", "Oxford University Press"),
    # Default: keep first publisher before slash
    (r"^([^/]+?)\s*/\s*.+$", r"\1"),
]


def auto_correct_publisher_name(name: str) -> str:
    """Apply auto-correction rules to normalize a publisher name.

    Rules applied (in order):
    1. Strip whitespace
    2. Remove parenthetical content (edition info, series names)
    3. Handle dual publishers (keep primary)
    4. Remove location suffixes
    5. Expand known abbreviations
    6. Normalize punctuation (& Co -> & Co.)

    Args:
        name: Raw publisher name

    Returns:
        Normalized publisher name
    """
    if not name:
        return name

    # Strip whitespace
    result = name.strip()

    # Remove parenthetical content
    result = re.sub(r"\s*\([^)]+\)\s*", " ", result).strip()

    # Handle dual publishers
    for pattern, replacement in DUAL_PUBLISHER_RULES:
        result = re.sub(pattern, replacement, result).strip()

    # Remove location suffixes
    for suffix_pattern in LOCATION_SUFFIXES:
        result = re.sub(suffix_pattern, "", result, flags=re.IGNORECASE).strip()

    # Expand known abbreviations
    for abbrev, expansion in ABBREVIATION_EXPANSIONS.items():
        if result == abbrev or result.startswith(abbrev + " "):
            result = result.replace(abbrev, expansion, 1)

    # Normalize "& Co" to "& Co."
    result = re.sub(r"&\s*Co(?!\.)(\s|$)", r"& Co.\1", result)

    # Final whitespace cleanup
    result = " ".join(result.split())

    return result
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestAutoCorrectPublisherName -v`
Expected: All tests PASS

**Step 3: Commit**

Run: `git add backend/app/services/publisher_validation.py`
Run: `git commit -m "feat: implement publisher name auto-correction rules"`

---

### Task 4: Write failing tests for publisher tier mappings

**Files:**

- Modify: `backend/tests/test_publisher_validation.py`

**Step 1: Add failing tests**

Append to the test file:

```python
from app.services.publisher_validation import normalize_publisher_name


class TestNormalizePublisherName:
    """Test publisher name normalization and tier assignment."""

    def test_tier_1_macmillan(self):
        name, tier = normalize_publisher_name("Macmillan and Co.")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"

    def test_tier_1_chapman_hall(self):
        name, tier = normalize_publisher_name("Chapman & Hall")
        assert name == "Chapman & Hall"
        assert tier == "TIER_1"

    def test_tier_1_smith_elder(self):
        name, tier = normalize_publisher_name("Smith, Elder & Co.")
        assert name == "Smith, Elder & Co."
        assert tier == "TIER_1"

    def test_tier_1_john_murray(self):
        name, tier = normalize_publisher_name("John Murray")
        assert name == "John Murray"
        assert tier == "TIER_1"

    def test_tier_1_oxford_university_press(self):
        name, tier = normalize_publisher_name("Oxford University Press")
        assert name == "Oxford University Press"
        assert tier == "TIER_1"

    def test_tier_1_longmans(self):
        name, tier = normalize_publisher_name("Longmans, Green & Co.")
        assert name == "Longmans, Green & Co."
        assert tier == "TIER_1"

    def test_tier_1_harper_brothers(self):
        name, tier = normalize_publisher_name("Harper & Brothers")
        assert name == "Harper & Brothers"
        assert tier == "TIER_1"

    def test_tier_2_chatto_windus(self):
        name, tier = normalize_publisher_name("Chatto and Windus")
        assert name == "Chatto and Windus"
        assert tier == "TIER_2"

    def test_tier_2_george_allen(self):
        name, tier = normalize_publisher_name("George Allen")
        assert name == "George Allen"
        assert tier == "TIER_2"

    def test_unknown_publisher_no_tier(self):
        name, tier = normalize_publisher_name("Unknown Publisher")
        assert name == "Unknown Publisher"
        assert tier is None

    def test_applies_auto_correct_first(self):
        # Should remove location suffix, then match tier
        name, tier = normalize_publisher_name("Harper & Brothers, New York")
        assert name == "Harper & Brothers"
        assert tier == "TIER_1"

    def test_case_insensitive_matching(self):
        name, tier = normalize_publisher_name("MACMILLAN AND CO.")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestNormalizePublisherName -v`
Expected: FAIL with "cannot import name 'normalize_publisher_name'"

**Step 3: Commit failing tests**

Run: `git add backend/tests/test_publisher_validation.py`
Run: `git commit -m "test: add failing tests for publisher tier normalization"`

---

### Task 5: Implement normalize_publisher_name with tier mappings

**Files:**

- Modify: `backend/app/services/publisher_validation.py`

**Step 1: Add tier mappings and normalize function**

Add to the file after the auto_correct function:

```python
# Publisher tier mappings based on market recognition and historical significance
# Maps variant names to (canonical_name, tier)
TIER_1_PUBLISHERS = {
    # Major Victorian/Edwardian publishers
    "Macmillan and Co.": "Macmillan and Co.",
    "Macmillan": "Macmillan and Co.",
    "Chapman & Hall": "Chapman & Hall",
    "Chapman and Hall": "Chapman & Hall",
    "Smith, Elder & Co.": "Smith, Elder & Co.",
    "Smith Elder": "Smith, Elder & Co.",
    "John Murray": "John Murray",
    "Murray": "John Murray",
    "William Blackwood and Sons": "William Blackwood and Sons",
    "Blackwood": "William Blackwood and Sons",
    "Edward Moxon and Co.": "Edward Moxon and Co.",
    "Moxon": "Edward Moxon and Co.",
    "Oxford University Press": "Oxford University Press",
    "OUP": "Oxford University Press",
    "Longmans, Green & Co.": "Longmans, Green & Co.",
    "Longmans": "Longmans, Green & Co.",
    "Longman": "Longmans, Green & Co.",
    "Harper & Brothers": "Harper & Brothers",
    "Harper": "Harper & Brothers",
    "D. Appleton and Company": "D. Appleton and Company",
    "Appleton": "D. Appleton and Company",
    "Little, Brown, and Company": "Little, Brown, and Company",
    "Little Brown": "Little, Brown, and Company",
    "Richard Bentley": "Richard Bentley",
    "Bentley": "Richard Bentley",
}

TIER_2_PUBLISHERS = {
    "Chatto and Windus": "Chatto and Windus",
    "Chatto & Windus": "Chatto and Windus",
    "George Allen": "George Allen",
    "Cassell": "Cassell, Petter & Galpin",
    "Cassell, Petter & Galpin": "Cassell, Petter & Galpin",
    "Routledge": "Routledge",
    "Ward, Lock & Co.": "Ward, Lock & Co.",
    "Ward Lock": "Ward, Lock & Co.",
    "Hurst & Company": "Hurst & Company",
    "Grosset & Dunlap": "Grosset & Dunlap",
}


def normalize_publisher_name(name: str) -> tuple[str, str | None]:
    """Normalize publisher name and determine tier.

    Applies auto-correction rules first, then matches against known publishers.

    Args:
        name: Raw publisher name from analysis

    Returns:
        Tuple of (canonical_name, tier) where tier is TIER_1, TIER_2, or None
    """
    # Apply auto-correction first
    corrected = auto_correct_publisher_name(name)

    # Check Tier 1 first
    for variant, canonical in TIER_1_PUBLISHERS.items():
        if variant.lower() == corrected.lower():
            return canonical, "TIER_1"
        # Also check if variant is contained in the name
        if variant.lower() in corrected.lower():
            return canonical, "TIER_1"

    # Check Tier 2
    for variant, canonical in TIER_2_PUBLISHERS.items():
        if variant.lower() == corrected.lower():
            return canonical, "TIER_2"
        if variant.lower() in corrected.lower():
            return canonical, "TIER_2"

    # Unknown publisher - return corrected name with no tier
    return corrected, None
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestNormalizePublisherName -v`
Expected: All tests PASS

**Step 3: Commit**

Run: `git add backend/app/services/publisher_validation.py`
Run: `git commit -m "feat: implement publisher tier normalization with known publishers"`

---

## Phase 2: Fuzzy Matching Service

### Task 6: Write failing tests for fuzzy matching

**Files:**

- Modify: `backend/tests/test_publisher_validation.py`

**Step 1: Add failing tests**

Append to test file:

```python
from app.services.publisher_validation import (
    fuzzy_match_publisher,
    PublisherMatch,
)


class TestFuzzyMatchPublisher:
    """Test fuzzy matching against existing publishers."""

    def test_exact_match_returns_high_confidence(self, db):
        from app.models.publisher import Publisher

        # Create existing publisher
        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_publisher(db, "Harper & Brothers")
        assert len(matches) >= 1
        assert matches[0].name == "Harper & Brothers"
        assert matches[0].confidence >= 0.95
        assert matches[0].publisher_id == pub.id

    def test_close_match_returns_medium_confidence(self, db):
        from app.models.publisher import Publisher

        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        # Typo in name
        matches = fuzzy_match_publisher(db, "Harpr & Brothers")
        assert len(matches) >= 1
        assert matches[0].name == "Harper & Brothers"
        assert 0.6 <= matches[0].confidence < 0.95

    def test_no_match_returns_empty(self, db):
        from app.models.publisher import Publisher

        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_publisher(db, "Completely Different Publisher")
        assert len(matches) == 0 or matches[0].confidence < 0.6

    def test_returns_top_3_matches(self, db):
        from app.models.publisher import Publisher

        # Create several publishers
        db.add(Publisher(name="Harper & Brothers", tier="TIER_1"))
        db.add(Publisher(name="Harper & Row", tier="TIER_2"))
        db.add(Publisher(name="Harpers Magazine", tier=None))
        db.add(Publisher(name="Macmillan", tier="TIER_1"))
        db.flush()

        matches = fuzzy_match_publisher(db, "Harper")
        assert len(matches) <= 3
        # All returned should have Harper in name
        for match in matches:
            assert "Harper" in match.name or match.confidence > 0.5

    def test_match_includes_tier(self, db):
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan and Co.", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_publisher(db, "Macmillan")
        assert len(matches) >= 1
        assert matches[0].tier == "TIER_1"
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestFuzzyMatchPublisher -v`
Expected: FAIL with "cannot import name 'fuzzy_match_publisher'"

**Step 3: Commit failing tests**

Run: `git add backend/tests/test_publisher_validation.py`
Run: `git commit -m "test: add failing tests for publisher fuzzy matching"`

---

### Task 7: Implement fuzzy matching

**Files:**

- Modify: `backend/app/services/publisher_validation.py`

**Step 1: Add imports and dataclass at top of file**

```python
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy.orm import Session
```

**Step 2: Add PublisherMatch dataclass and fuzzy_match function**

Add after the normalize function:

```python
@dataclass
class PublisherMatch:
    """Result of fuzzy matching a publisher name."""

    publisher_id: int
    name: str
    tier: str | None
    confidence: float  # 0.0 to 1.0


def fuzzy_match_publisher(
    db: Session,
    name: str,
    threshold: float = 0.6,
    max_results: int = 3,
) -> list[PublisherMatch]:
    """Find existing publishers that fuzzy-match the given name.

    Args:
        db: Database session
        name: Publisher name to match
        threshold: Minimum confidence score (0.0 to 1.0)
        max_results: Maximum number of matches to return

    Returns:
        List of PublisherMatch objects, sorted by confidence descending
    """
    from app.models.publisher import Publisher

    # Apply auto-correction before matching
    corrected_name = auto_correct_publisher_name(name)

    # Get all publishers
    publishers = db.query(Publisher).all()

    matches = []
    for pub in publishers:
        # Calculate similarity ratio (0-100 scale from rapidfuzz)
        ratio = fuzz.ratio(corrected_name.lower(), pub.name.lower()) / 100.0

        # Also try token sort ratio for word order independence
        token_ratio = fuzz.token_sort_ratio(corrected_name.lower(), pub.name.lower()) / 100.0

        # Use the higher of the two scores
        confidence = max(ratio, token_ratio)

        if confidence >= threshold:
            matches.append(
                PublisherMatch(
                    publisher_id=pub.id,
                    name=pub.name,
                    tier=pub.tier,
                    confidence=confidence,
                )
            )

    # Sort by confidence descending, take top N
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches[:max_results]
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestFuzzyMatchPublisher -v`
Expected: All tests PASS

**Step 3: Commit**

Run: `git add backend/app/services/publisher_validation.py`
Run: `git commit -m "feat: implement fuzzy matching for publishers"`

---

## Phase 3: Get or Create Publisher Service

### Task 8: Write failing tests for get_or_create_publisher

**Files:**

- Modify: `backend/tests/test_publisher_validation.py`

**Step 1: Add failing tests**

Append to test file:

```python
from app.services.publisher_validation import get_or_create_publisher


class TestGetOrCreatePublisher:
    """Test publisher lookup/creation from parsed data."""

    def test_returns_none_for_none_input(self, db):
        result = get_or_create_publisher(db, None)
        assert result is None

    def test_returns_none_for_empty_string(self, db):
        result = get_or_create_publisher(db, "")
        assert result is None

    def test_creates_tier_1_publisher(self, db):
        result = get_or_create_publisher(db, "Macmillan and Co.")
        assert result is not None
        assert result.name == "Macmillan and Co."
        assert result.tier == "TIER_1"
        assert result.id is not None

    def test_creates_unknown_publisher_no_tier(self, db):
        result = get_or_create_publisher(db, "Unknown Local Press")
        assert result is not None
        assert result.name == "Unknown Local Press"
        assert result.tier is None

    def test_returns_existing_publisher_exact_match(self, db):
        # Create first
        first = get_or_create_publisher(db, "Harper & Brothers")
        db.flush()

        # Look up again
        second = get_or_create_publisher(db, "Harper & Brothers")
        assert second.id == first.id

    def test_returns_existing_publisher_fuzzy_match(self, db):
        # Create first
        first = get_or_create_publisher(db, "Harper & Brothers")
        db.flush()

        # Look up with typo - should still match
        second = get_or_create_publisher(db, "Harpr & Brothers")
        assert second.id == first.id

    def test_applies_auto_correction(self, db):
        result = get_or_create_publisher(db, "Harper & Brothers, New York")
        assert result.name == "Harper & Brothers"
        assert result.tier == "TIER_1"

    def test_updates_tier_if_missing(self, db):
        from app.models.publisher import Publisher

        # Create publisher without tier manually
        pub = Publisher(name="Macmillan and Co.", tier=None)
        db.add(pub)
        db.flush()

        # Get via service - should update tier
        result = get_or_create_publisher(db, "Macmillan and Co.")
        assert result.id == pub.id
        assert result.tier == "TIER_1"

    def test_flags_new_publisher_for_enrichment(self, db):
        result = get_or_create_publisher(db, "New Unknown Publisher")
        assert result is not None
        assert result.description is None  # Not enriched yet
        # New publishers should exist but without enrichment
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestGetOrCreatePublisher -v`
Expected: FAIL with "cannot import name 'get_or_create_publisher'"

**Step 3: Commit failing tests**

Run: `git add backend/tests/test_publisher_validation.py`
Run: `git commit -m "test: add failing tests for get_or_create_publisher"`

---

### Task 9: Implement get_or_create_publisher

**Files:**

- Modify: `backend/app/services/publisher_validation.py`

**Step 1: Add function**

```python
def get_or_create_publisher(
    db: Session,
    name: str | None,
    high_confidence_threshold: float = 0.90,
) -> "Publisher | None":
    """Look up or create a publisher from a name string.

    Applies auto-correction, checks for existing matches via fuzzy matching,
    and creates new publisher if no good match found.

    Args:
        db: Database session
        name: Raw publisher name
        high_confidence_threshold: Confidence above which to auto-accept match

    Returns:
        Publisher instance or None if name is empty
    """
    from app.models.publisher import Publisher

    if not name or not name.strip():
        return None

    # Normalize name and get suggested tier
    canonical_name, tier = normalize_publisher_name(name)

    # Try exact match first
    publisher = db.query(Publisher).filter(Publisher.name == canonical_name).first()

    if publisher:
        # Update tier if we have new information and current tier is null
        if tier and not publisher.tier:
            publisher.tier = tier
        return publisher

    # Try fuzzy match
    matches = fuzzy_match_publisher(db, canonical_name, threshold=high_confidence_threshold)
    if matches and matches[0].confidence >= high_confidence_threshold:
        # High confidence match - use existing
        publisher = db.query(Publisher).filter(Publisher.id == matches[0].publisher_id).first()
        if publisher and tier and not publisher.tier:
            publisher.tier = tier
        return publisher

    # No good match - create new publisher
    publisher = Publisher(
        name=canonical_name,
        tier=tier,
    )
    db.add(publisher)
    db.flush()  # Get the ID without committing

    return publisher
```

**Step 2: Add Publisher import at module level**

At top of file, update imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.publisher import Publisher
```

**Step 3: Run tests to verify they pass**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestGetOrCreatePublisher -v`
Expected: All tests PASS

**Step 4: Commit**

Run: `git add backend/app/services/publisher_validation.py`
Run: `git commit -m "feat: implement get_or_create_publisher with fuzzy matching"`

---

## Phase 4: Integration with Analysis Pipeline

### Task 10: Write failing tests for publisher extraction from markdown

**Files:**

- Modify: `backend/tests/test_markdown_parser.py`

**Step 1: Add failing tests**

Add to the test file:

```python
class TestPublisherIdentification:
    """Test publisher identification extraction from markdown."""

    def test_extracts_publisher_from_structured_data(self):
        markdown = """
# Analysis

---STRUCTURED-DATA---
publisher_identified: Harper & Brothers
publisher_confidence: HIGH
---END-STRUCTURED-DATA---
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is not None
        assert result.publisher_identification["name"] == "Harper & Brothers"
        assert result.publisher_identification["confidence"] == "HIGH"

    def test_extracts_publisher_from_text_pattern(self):
        markdown = """
# Analysis

**Publisher:** Macmillan and Co., London
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is not None
        assert "Macmillan" in result.publisher_identification["name"]

    def test_returns_none_when_no_publisher(self):
        markdown = """
# Analysis

Just some text without publisher info.
"""
        result = parse_analysis_markdown(markdown)
        assert result.publisher_identification is None
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && poetry run pytest tests/test_markdown_parser.py::TestPublisherIdentification -v`
Expected: FAIL with AttributeError: 'ParsedAnalysis' object has no attribute 'publisher_identification'

**Step 3: Commit failing tests**

Run: `git add backend/tests/test_markdown_parser.py`
Run: `git commit -m "test: add failing tests for publisher extraction from markdown"`

---

### Task 11: Add publisher_identification to ParsedAnalysis

**Files:**

- Modify: `backend/app/utils/markdown_parser.py`

**Step 1: Add field to ParsedAnalysis dataclass**

Add after `binder_identification`:

```python
    publisher_identification: dict | None = None
```

**Step 2: Add _parse_publisher_identification function**

Add after `_parse_binder_identification`:

```python
def _parse_publisher_identification(markdown: str) -> dict | None:
    """Extract publisher identification from markdown.

    Looks for:
    - Structured data block: publisher_identified: Name
    - Text pattern: **Publisher:** Name
    """
    result: dict = {}

    # Check structured data first
    structured = _parse_structured_data(markdown)
    if structured and structured.get("publisher_identified"):
        result["name"] = structured["publisher_identified"]
        if structured.get("publisher_confidence"):
            result["confidence"] = structured["publisher_confidence"].upper()

    # Also check for **Publisher:** pattern
    if "name" not in result:
        publisher_match = re.search(r"\*\*Publisher:\*\*\s*(.+)", markdown)
        if publisher_match:
            name = publisher_match.group(1).strip()
            # Remove trailing location info for now (will be auto-corrected later)
            result["name"] = name

    return result if result else None
```

**Step 3: Call parser in parse_analysis_markdown function**

In `parse_analysis_markdown`, add before the return statement:

```python
    # Extract publisher identification
    publisher_identification = _parse_publisher_identification(markdown)
```

Update the return to include it:

```python
    return ParsedAnalysis(
        executive_summary=sections.get("executive_summary"),
        historical_significance=sections.get("historical_significance"),
        condition_assessment=(
            _parse_condition_assessment(sections["condition_assessment"])
            if "condition_assessment" in sections
            else None
        ),
        market_analysis=(
            _parse_market_analysis(sections["market_analysis"])
            if "market_analysis" in sections
            else None
        ),
        recommendations=sections.get("recommendations"),
        structured_data=structured_data,
        binder_identification=binder_identification,
        publisher_identification=publisher_identification,
    )
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && poetry run pytest tests/test_markdown_parser.py::TestPublisherIdentification -v`
Expected: All tests PASS

**Step 5: Commit**

Run: `git add backend/app/utils/markdown_parser.py`
Run: `git commit -m "feat: extract publisher identification from analysis markdown"`

---

### Task 12: Write failing test for publisher integration in analysis save

**Files:**

- Modify: `backend/tests/test_books.py`

**Step 1: Add failing test**

Add to test file:

```python
class TestAnalysisPublisherIntegration:
    """Test publisher extraction and linking during analysis save."""

    def test_update_analysis_links_publisher(self, client, db, mock_editor_auth):
        from app.models import Book

        # Create book without publisher
        book = Book(title="Test Book", category="Fiction")
        db.add(book)
        db.commit()

        # Upload analysis with publisher info
        markdown = """
# Analysis

---STRUCTURED-DATA---
publisher_identified: Harper & Brothers
publisher_confidence: HIGH
---END-STRUCTURED-DATA---

## Executive Summary
Test book analysis.
"""
        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=markdown,
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("publisher_updated") is True

        # Verify publisher linked
        db.refresh(book)
        assert book.publisher is not None
        assert book.publisher.name == "Harper & Brothers"
        assert book.publisher.tier == "TIER_1"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_books.py::TestAnalysisPublisherIntegration -v`
Expected: FAIL (publisher_updated not in response, or publisher not linked)

**Step 3: Commit failing test**

Run: `git add backend/tests/test_books.py`
Run: `git commit -m "test: add failing test for publisher linking in analysis save"`

---

### Task 13: Integrate publisher validation into update_book_analysis

**Files:**

- Modify: `backend/app/api/v1/books.py`

**Step 1: Add import**

After the existing reference import, add:

```python
    from app.services.publisher_validation import get_or_create_publisher
```

**Step 2: Add publisher extraction logic**

After the binder extraction section (around line 1401), add:

```python
    # Extract publisher identification and associate with book
    publisher_updated = False
    if parsed.publisher_identification:
        publisher = get_or_create_publisher(
            db, parsed.publisher_identification.get("name")
        )
        if publisher and book.publisher_id != publisher.id:
            book.publisher_id = publisher.id
            publisher_updated = True
```

**Step 3: Update return statement**

Add `publisher_updated` to the return dict:

```python
    return {
        "message": "Analysis updated",
        "values_updated": values_changed,
        "binder_updated": binder_updated,
        "publisher_updated": publisher_updated,
        "metadata_updated": metadata_updated,
        "scores_recalculated": True,
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_books.py::TestAnalysisPublisherIntegration -v`
Expected: PASS

**Step 5: Commit**

Run: `git add backend/app/api/v1/books.py`
Run: `git commit -m "feat: integrate publisher validation into analysis save"`

---

## Phase 5: Full Test Suite and Linting

### Task 14: Run full test suite

**Step 1: Run all tests**

Run: `cd backend && poetry run pytest -v`
Expected: All tests PASS

**Step 2: Run linting**

Run: `cd backend && poetry run ruff check .`
Expected: No errors

Run: `cd backend && poetry run ruff format --check .`
Expected: No formatting issues (or run `ruff format .` to fix)

**Step 3: Commit any fixes**

Run: `git add -A`
Run: `git commit -m "chore: fix linting issues"`

---

## Phase 6: Deployment

### Task 15: Create PR and deploy to staging

**Step 1: Push branch**

Run: `git push -u origin feat/smart-publisher-validation`

**Step 2: Create PR to staging**

Run: `gh pr create --base staging --title "feat: Smart publisher validation layer" --body "## Summary

- Add publisher validation layer with auto-correction rules
- Implement fuzzy matching against existing publishers
- Auto-assign tiers based on known Victorian publishers
- Extract publisher from analysis markdown and link to book
- Follow binder service pattern for consistency

## Test Plan

- [ ] All unit tests pass
- [ ] Manual test: upload analysis with publisher info
- [ ] Verify publisher linked correctly
- [ ] Verify new publishers created with correct tier"`

**Step 3: Wait for CI**

Run: `gh pr checks --watch`
Expected: All checks pass

**Step 4: Merge to staging**

Run: `gh pr merge --squash --auto`

---

### Task 16: Validate in staging

**Step 1: Check staging health**

Run: `curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq '.status'`
Expected: "healthy"

**Step 2: Test publisher validation manually**

Run: `bmx-api GET /publishers | jq 'length'`
Note the count.

**Step 3: Create test book and upload analysis**

Create a test in staging via API and verify publisher linking works.

---

### Task 17: Promote to production

**Step 1: Create PR from staging to main**

Run: `gh pr create --base main --head staging --title "chore: Promote staging to production - Smart publisher validation"`

**Step 2: Wait for CI and merge**

Run: `gh pr checks --watch`
Run: `gh pr merge --squash`

**Step 3: Watch deploy**

Run: `gh run list --workflow Deploy --limit 1`
Run: `gh run watch <run-id> --exit-status`

**Step 4: Verify production**

Run: `bmx-api --prod GET /publishers | jq 'length'`
Run: `curl -s https://api.bluemoxon.com/api/v1/health/deep | jq '.status'`

---

## Summary

This plan implements smart publisher validation in 17 bite-sized tasks:

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-5 | Foundation: auto-correct rules, tier mappings |
| 2 | 6-7 | Fuzzy matching with rapidfuzz |
| 3 | 8-9 | get_or_create_publisher service |
| 4 | 10-13 | Integration with analysis pipeline |
| 5 | 14 | Full test suite validation |
| 6 | 15-17 | Deployment through staging to production |

Each task follows strict TDD: write failing test, verify failure, implement, verify pass, commit.

---

## Phase 7: Code Review Fixes (2025-12-23)

### Code Review Findings

After initial deployment, a code review identified 8 issues:

| Priority | Issue | Status |
|----------|-------|--------|
| 🔴 Critical | #1: Greedy substring matching in tier lookup | **Fixed** |
| 🔴 Critical | #3: Race condition handling with `db.rollback()` | **Fixed** |
| 🟡 Medium | #2: O(n) table scan for fuzzy matching | Deferred → #575 |
| 🟡 Medium | #5: No audit trail for publisher changes | Deferred → #576 |
| 🟡 Medium | #6: Hardcoded tier dictionaries | Deferred → #577 |
| 🟢 Low | #4: Canonical name not used when substring matches | Fixed with #1 |
| 🟢 Low | #7: Magic number 90% threshold | Acceptable, documented |
| 🟢 Low | #8: Abbreviation expansion fragile | Acceptable, works for known cases |

---

### Task 18: Fix greedy substring matching

**Problem:** `normalize_publisher_name()` used `if variant.lower() in corrected.lower()` which matched "Murray Printing Company" to "John Murray" as TIER_1.

**Files:**

- Modify: `backend/app/services/publisher_validation.py`
- Modify: `backend/tests/test_publisher_validation.py`

**Step 1: Add regression tests**

```python
def test_no_substring_matching_murray(self):
    # "Murray Printing Company" should NOT match "John Murray"
    name, tier = normalize_publisher_name("Murray Printing Company")
    assert name == "Murray Printing Company"
    assert tier is None  # NOT TIER_1

def test_no_substring_matching_harper(self):
    # "Harper's Magazine Press" should NOT match "Harper & Brothers"
    name, tier = normalize_publisher_name("Harper's Magazine Press")
    assert name == "Harper's Magazine Press"
    assert tier is None  # NOT TIER_1

def test_no_substring_matching_appleton(self):
    # "Appleton Wisconsin Books" should NOT match "D. Appleton and Company"
    name, tier = normalize_publisher_name("Appleton Wisconsin Books")
    assert name == "Appleton Wisconsin Books"
    assert tier is None  # NOT TIER_1
```

**Step 2: Fix the matching logic**

Remove substring matching - use exact match only (case-insensitive):

```python
# Check Tier 1 first (exact match only, case-insensitive)
for variant, canonical in TIER_1_PUBLISHERS.items():
    if variant.lower() == corrected.lower():
        return canonical, "TIER_1"

# Check Tier 2 (exact match only, case-insensitive)
for variant, canonical in TIER_2_PUBLISHERS.items():
    if variant.lower() == corrected.lower():
        return canonical, "TIER_2"
```

**Verification:** 42 tests pass, no false positive tier matches.

---

### Task 19: Fix race condition handling

**Problem:** Original code used `db.rollback()` which nukes the entire transaction, potentially rolling back the caller's pending changes.

**Files:**

- Modify: `backend/app/services/publisher_validation.py`

**Before (broken):**

```python
try:
    db.flush()
except IntegrityError:
    db.rollback()  # BROKEN: nukes entire transaction!
    publisher = db.query(Publisher).filter(Publisher.name == canonical_name).first()
return publisher  # Can be None!
```

**After (correct with savepoint):**

```python
from sqlalchemy.exc import IntegrityError

# ...

try:
    with db.begin_nested():  # Savepoint - only rolls back this block on error
        db.add(publisher)
        db.flush()
except IntegrityError:
    # Another request created this publisher - fetch the existing one
    # Savepoint was rolled back, but parent transaction is intact
    publisher = db.query(Publisher).filter(Publisher.name == canonical_name).first()
    if publisher is None:
        # Should not happen, but guard against it
        raise RuntimeError(
            f"Race condition in publisher creation for '{canonical_name}' "
            "but could not find existing record"
        ) from None

return publisher
```

**Key changes:**

1. Use `db.begin_nested()` for savepoint - only rolls back the nested block, not caller's transaction
2. Add RuntimeError guard if publisher is None after IntegrityError (should never happen, but defensive)
3. Added `from None` to satisfy linter (B904)

**Verification:** 42 tests pass, linter clean.

---

### Task 20: Create GitHub issues for deferred work

Created issues for future improvements:

- **#575**: Use pg_trgm for O(1) fuzzy matching (addresses #2)
- **#576**: Add publisher change audit trail (addresses #5)
- **#577**: Load tier mappings from database (addresses #6)

---

### Task 21: Deploy code review fixes

**PRs merged:**

- **#578**: fix: publisher validation - remove greedy substring matching and add race condition handling (staging)
- **#579**: chore: Promote staging to production - Savepoint fix for race condition

**Verification:**

- ✅ 42/42 tests pass locally
- ✅ Linter passes
- ✅ Staging deploy + smoke tests passed
- ✅ Production deploy + smoke tests passed
- ✅ Production publishers endpoint verified working

---

## Final Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-5 | Foundation: auto-correct rules, tier mappings |
| 2 | 6-7 | Fuzzy matching with rapidfuzz |
| 3 | 8-9 | get_or_create_publisher service |
| 4 | 10-13 | Integration with analysis pipeline |
| 5 | 14 | Full test suite validation |
| 6 | 15-17 | Deployment through staging to production |
| **7** | **18-21** | **Code review fixes (2025-12-23)** |

Total: 21 tasks completed across 7 phases.
