# Scoring Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add automated scoring to help prioritize book acquisitions with Investment Grade, Strategic Fit, and Collection Impact scores.

**Architecture:** Backend scoring service calculates three component scores + overall composite. Scores stored on books table, auto-calculated on create, on-demand refresh. Frontend displays score breakdown cards on Acquisitions Dashboard.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Vue 3, Pinia, TailwindCSS

---

## Task 1: Add priority_score Field to Authors Model

**Files:**

- Modify: `backend/app/models/author.py`
- Test: `backend/tests/test_scoring.py` (new)

### Step 1: Write the failing test

Create `backend/tests/test_scoring.py`:

```python
"""Scoring engine tests."""

import pytest
from app.models.author import Author


class TestAuthorPriorityScore:
    """Tests for author priority_score field."""

    def test_author_has_priority_score_field(self, db):
        """Author model should have priority_score field defaulting to 0."""
        author = Author(name="Test Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        assert hasattr(author, "priority_score")
        assert author.priority_score == 0

    def test_author_priority_score_can_be_set(self, db):
        """Author priority_score can be set to custom value."""
        author = Author(name="Thomas Hardy", priority_score=50)
        db.add(author)
        db.commit()
        db.refresh(author)

        assert author.priority_score == 50
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py -v
```

Expected: FAIL with `AttributeError: type object 'Author' has no attribute 'priority_score'`

### Step 3: Add priority_score to Author model

Modify `backend/app/models/author.py`, add after line 21 (after `first_acquired_date`):

```python
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py -v
```

Expected: PASS

### Step 5: Commit

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/acquisitions-dashboard
git add backend/app/models/author.py backend/tests/test_scoring.py
git commit -m "feat: add priority_score field to Author model"
```

---

## Task 2: Add Score Fields to Book Model

**Files:**

- Modify: `backend/app/models/book.py`
- Modify: `backend/tests/test_scoring.py`

### Step 1: Write the failing test

Add to `backend/tests/test_scoring.py`:

```python
from datetime import datetime
from app.models.book import Book


class TestBookScoreFields:
    """Tests for book score fields."""

    def test_book_has_score_fields(self, db):
        """Book model should have all score fields."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        db.refresh(book)

        assert hasattr(book, "investment_grade")
        assert hasattr(book, "strategic_fit")
        assert hasattr(book, "collection_impact")
        assert hasattr(book, "overall_score")
        assert hasattr(book, "scores_calculated_at")

    def test_book_score_fields_default_to_none(self, db):
        """Score fields should default to None."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.investment_grade is None
        assert book.strategic_fit is None
        assert book.collection_impact is None
        assert book.overall_score is None
        assert book.scores_calculated_at is None
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestBookScoreFields -v
```

Expected: FAIL with `AttributeError`

### Step 3: Add score fields to Book model

Modify `backend/app/models/book.py`, add after line 77 (after `scoring_snapshot`):

```python
    # Calculated scores
    investment_grade: Mapped[int | None] = mapped_column(Integer)
    strategic_fit: Mapped[int | None] = mapped_column(Integer)
    collection_impact: Mapped[int | None] = mapped_column(Integer)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    scores_calculated_at: Mapped[datetime | None] = mapped_column(DateTime)
```

Also add to imports at top of file:

```python
from datetime import date, datetime
```

And add to SQLAlchemy imports:

```python
from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestBookScoreFields -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/models/book.py backend/tests/test_scoring.py
git commit -m "feat: add score fields to Book model"
```

---

## Task 3: Create Scoring Service with Investment Grade Calculator

**Files:**

- Create: `backend/app/services/scoring.py`
- Modify: `backend/tests/test_scoring.py`

### Step 1: Write the failing test

Add to `backend/tests/test_scoring.py`:

```python
from decimal import Decimal
from app.services.scoring import calculate_investment_grade


class TestInvestmentGrade:
    """Tests for investment grade calculation."""

    def test_exceptional_discount_70_plus(self):
        """70%+ discount should score 100."""
        score = calculate_investment_grade(
            purchase_price=Decimal("100"),
            value_mid=Decimal("400")  # 75% discount
        )
        assert score == 100

    def test_strong_discount_60_to_69(self):
        """60-69% discount should score 85."""
        score = calculate_investment_grade(
            purchase_price=Decimal("350"),
            value_mid=Decimal("1000")  # 65% discount
        )
        assert score == 85

    def test_good_discount_50_to_59(self):
        """50-59% discount should score 70."""
        score = calculate_investment_grade(
            purchase_price=Decimal("450"),
            value_mid=Decimal("1000")  # 55% discount
        )
        assert score == 70

    def test_meets_minimum_40_to_49(self):
        """40-49% discount should score 55."""
        score = calculate_investment_grade(
            purchase_price=Decimal("550"),
            value_mid=Decimal("1000")  # 45% discount
        )
        assert score == 55

    def test_below_target_30_to_39(self):
        """30-39% discount should score 35."""
        score = calculate_investment_grade(
            purchase_price=Decimal("650"),
            value_mid=Decimal("1000")  # 35% discount
        )
        assert score == 35

    def test_marginal_20_to_29(self):
        """20-29% discount should score 20."""
        score = calculate_investment_grade(
            purchase_price=Decimal("750"),
            value_mid=Decimal("1000")  # 25% discount
        )
        assert score == 20

    def test_poor_under_20(self):
        """Under 20% discount should score 5."""
        score = calculate_investment_grade(
            purchase_price=Decimal("900"),
            value_mid=Decimal("1000")  # 10% discount
        )
        assert score == 5

    def test_no_price_data_returns_zero(self):
        """Missing price data should score 0."""
        assert calculate_investment_grade(None, Decimal("1000")) == 0
        assert calculate_investment_grade(Decimal("100"), None) == 0
        assert calculate_investment_grade(None, None) == 0

    def test_negative_discount_returns_five(self):
        """Overpaying (negative discount) should score 5."""
        score = calculate_investment_grade(
            purchase_price=Decimal("1200"),
            value_mid=Decimal("1000")  # -20% "discount"
        )
        assert score == 5
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestInvestmentGrade -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.scoring'`

### Step 3: Create scoring service

Create `backend/app/services/scoring.py`:

```python
"""Scoring engine for book acquisition evaluation."""

from decimal import Decimal


def calculate_investment_grade(
    purchase_price: Decimal | None,
    value_mid: Decimal | None,
) -> int:
    """
    Calculate investment grade based on discount percentage.

    Returns score 0-100:
    - 70%+ discount: 100
    - 60-69%: 85
    - 50-59%: 70
    - 40-49%: 55
    - 30-39%: 35
    - 20-29%: 20
    - <20%: 5
    - No data: 0
    """
    if purchase_price is None or value_mid is None:
        return 0

    if value_mid <= 0:
        return 0

    discount_pct = float((value_mid - purchase_price) / value_mid * 100)

    if discount_pct >= 70:
        return 100
    elif discount_pct >= 60:
        return 85
    elif discount_pct >= 50:
        return 70
    elif discount_pct >= 40:
        return 55
    elif discount_pct >= 30:
        return 35
    elif discount_pct >= 20:
        return 20
    else:
        return 5
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestInvestmentGrade -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat: add investment grade calculator to scoring service"
```

---

## Task 4: Add Strategic Fit Calculator

**Files:**

- Modify: `backend/app/services/scoring.py`
- Modify: `backend/tests/test_scoring.py`

### Step 1: Write the failing test

Add to `backend/tests/test_scoring.py`:

```python
from app.services.scoring import calculate_strategic_fit


class TestStrategicFit:
    """Tests for strategic fit calculation."""

    def test_tier_1_publisher_adds_35(self):
        """Tier 1 publisher should add 35 points."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 35

    def test_tier_2_publisher_adds_15(self):
        """Tier 2 publisher should add 15 points."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_2",
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 15

    def test_victorian_era_adds_20(self):
        """Victorian era (1837-1901) should add 20 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=1867,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 20

    def test_romantic_era_adds_20(self):
        """Romantic era (1800-1836) should add 20 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=1820,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 20

    def test_complete_set_adds_15(self):
        """Complete set should add 15 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=None,
            is_complete=True,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 15

    def test_good_condition_adds_15(self):
        """Good or better condition should add 15 points."""
        for grade in ["Fine", "Very Good", "Good"]:
            score = calculate_strategic_fit(
                publisher_tier=None,
                year_start=None,
                is_complete=False,
                condition_grade=grade,
                author_priority_score=0,
            )
            assert score == 15, f"Failed for grade: {grade}"

    def test_author_priority_added(self):
        """Author priority score should be added directly."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=50,
        )
        assert score == 50

    def test_combined_factors(self):
        """All factors should combine additively."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",     # +35
            year_start=1867,             # +20 (Victorian)
            is_complete=True,            # +15
            condition_grade="Very Good", # +15
            author_priority_score=50,    # +50
        )
        assert score == 135  # 35 + 20 + 15 + 15 + 50
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestStrategicFit -v
```

Expected: FAIL with `ImportError`

### Step 3: Add strategic fit calculator

Add to `backend/app/services/scoring.py`:

```python
def calculate_strategic_fit(
    publisher_tier: str | None,
    year_start: int | None,
    is_complete: bool,
    condition_grade: str | None,
    author_priority_score: int,
) -> int:
    """
    Calculate strategic fit score based on collection criteria.

    Factors:
    - Tier 1 Publisher: +35
    - Tier 2 Publisher: +15
    - Victorian/Romantic Era: +20
    - Complete Set: +15
    - Good+ Condition: +15
    - Author Priority: variable (0-50)

    Returns score 0-100+ (can exceed 100 with high author priority).
    """
    score = 0

    # Publisher tier
    if publisher_tier == "TIER_1":
        score += 35
    elif publisher_tier == "TIER_2":
        score += 15

    # Era (Victorian 1837-1901, Romantic 1800-1836)
    if year_start is not None:
        if 1800 <= year_start <= 1901:
            score += 20

    # Complete set
    if is_complete:
        score += 15

    # Condition (Good or better)
    if condition_grade in ("Fine", "Very Good", "Good"):
        score += 15

    # Author priority
    score += author_priority_score

    return score
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestStrategicFit -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat: add strategic fit calculator to scoring service"
```

---

## Task 5: Add Collection Impact Calculator with Duplicate Detection

**Files:**

- Modify: `backend/app/services/scoring.py`
- Modify: `backend/tests/test_scoring.py`

### Step 1: Write the failing test

Add to `backend/tests/test_scoring.py`:

```python
from app.services.scoring import calculate_collection_impact, is_duplicate_title


class TestDuplicateDetection:
    """Tests for fuzzy title matching."""

    def test_exact_match_is_duplicate(self):
        """Exact title match should be detected as duplicate."""
        assert is_duplicate_title("Essays of Elia", "Essays of Elia") is True

    def test_case_insensitive_match(self):
        """Case differences should still match."""
        assert is_duplicate_title("Essays of Elia", "essays of elia") is True

    def test_article_differences_match(self):
        """Titles differing only by articles should match."""
        assert is_duplicate_title("The Water-Babies", "Water-Babies") is True

    def test_different_titles_not_duplicate(self):
        """Different titles should not match."""
        assert is_duplicate_title("Complete Works", "Poetical Works") is False

    def test_similar_but_different_not_duplicate(self):
        """Similar but distinct titles should not match."""
        assert is_duplicate_title("Essays of Elia", "Last Essays of Elia") is False


class TestCollectionImpact:
    """Tests for collection impact calculation."""

    def test_new_author_adds_30(self):
        """New author to collection should add 30 points."""
        score = calculate_collection_impact(
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
        )
        assert score == 30

    def test_fills_author_gap_adds_15(self):
        """Second book by author should add 15 points."""
        score = calculate_collection_impact(
            author_book_count=1,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
        )
        assert score == 15

    def test_third_book_no_bonus(self):
        """Third+ book by author gets no bonus."""
        score = calculate_collection_impact(
            author_book_count=2,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
        )
        assert score == 0

    def test_duplicate_subtracts_40(self):
        """Duplicate title should subtract 40 points."""
        score = calculate_collection_impact(
            author_book_count=0,
            is_duplicate=True,
            completes_set=False,
            volume_count=1,
        )
        assert score == -10  # 30 (new author) - 40 (duplicate)

    def test_completes_set_adds_25(self):
        """Completing a set should add 25 points."""
        score = calculate_collection_impact(
            author_book_count=2,
            is_duplicate=False,
            completes_set=True,
            volume_count=1,
        )
        assert score == 25

    def test_large_set_subtracts_20(self):
        """5+ volume set should subtract 20 points."""
        score = calculate_collection_impact(
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=6,
        )
        assert score == 10  # 30 (new author) - 20 (large set)
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestDuplicateDetection -v
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestCollectionImpact -v
```

Expected: FAIL with `ImportError`

### Step 3: Add collection impact calculator

Add to `backend/app/services/scoring.py`:

```python
import re


def normalize_title(title: str) -> str:
    """Normalize title for comparison: lowercase, remove articles/punctuation."""
    normalized = title.lower().strip()
    # Remove leading articles
    normalized = re.sub(r"^(the|a|an)\s+", "", normalized)
    # Remove possessive endings
    normalized = normalized.replace("'s", "")
    # Remove punctuation
    normalized = re.sub(r"[^\w\s]", "", normalized)
    # Normalize whitespace
    normalized = " ".join(normalized.split())
    return normalized


def is_duplicate_title(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """
    Check if two titles are duplicates using token-based similarity.

    Args:
        title1: First title
        title2: Second title
        threshold: Similarity threshold (0-1), default 0.8

    Returns:
        True if similarity >= threshold
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    # Exact match after normalization
    if norm1 == norm2:
        return True

    # Token-based similarity (Jaccard)
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    if not tokens1 or not tokens2:
        return False

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    similarity = intersection / union

    return similarity >= threshold


def calculate_collection_impact(
    author_book_count: int,
    is_duplicate: bool,
    completes_set: bool,
    volume_count: int,
) -> int:
    """
    Calculate collection impact score.

    Factors:
    - New author (0 existing): +30
    - Fills author gap (1 existing): +15
    - Duplicate title: -40
    - Completes incomplete set: +25
    - Large set penalty (5+ vols): -20

    Returns score (can be negative).
    """
    score = 0

    # Author presence bonus
    if author_book_count == 0:
        score += 30  # New author
    elif author_book_count == 1:
        score += 15  # Fills gap

    # Duplicate penalty
    if is_duplicate:
        score -= 40

    # Set completion bonus
    if completes_set:
        score += 25

    # Large set penalty
    if volume_count >= 5:
        score -= 20

    return score
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestDuplicateDetection -v
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestCollectionImpact -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat: add collection impact calculator with duplicate detection"
```

---

## Task 6: Add Full Score Calculation Function

**Files:**

- Modify: `backend/app/services/scoring.py`
- Modify: `backend/tests/test_scoring.py`

### Step 1: Write the failing test

Add to `backend/tests/test_scoring.py`:

```python
from app.services.scoring import calculate_all_scores


class TestCalculateAllScores:
    """Tests for full score calculation."""

    def test_returns_all_score_components(self):
        """Should return dict with all score components."""
        result = calculate_all_scores(
            purchase_price=Decimal("300"),
            value_mid=Decimal("1000"),
            publisher_tier="TIER_1",
            year_start=1867,
            is_complete=True,
            condition_grade="Very Good",
            author_priority_score=50,
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=3,
        )

        assert "investment_grade" in result
        assert "strategic_fit" in result
        assert "collection_impact" in result
        assert "overall_score" in result

    def test_overall_is_sum_of_components(self):
        """Overall score should be sum of components."""
        result = calculate_all_scores(
            purchase_price=Decimal("300"),
            value_mid=Decimal("1000"),  # 70% discount -> 100
            publisher_tier="TIER_1",     # +35
            year_start=1867,             # +20
            is_complete=True,            # +15
            condition_grade="Very Good", # +15
            author_priority_score=0,     # +0
            author_book_count=0,         # +30
            is_duplicate=False,          # +0
            completes_set=False,         # +0
            volume_count=3,              # +0
        )

        expected_investment = 100  # 70% discount
        expected_strategic = 35 + 20 + 15 + 15  # 85
        expected_collection = 30  # new author
        expected_overall = expected_investment + expected_strategic + expected_collection

        assert result["investment_grade"] == expected_investment
        assert result["strategic_fit"] == expected_strategic
        assert result["collection_impact"] == expected_collection
        assert result["overall_score"] == expected_overall
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestCalculateAllScores -v
```

Expected: FAIL with `ImportError`

### Step 3: Add calculate_all_scores function

Add to `backend/app/services/scoring.py`:

```python
def calculate_all_scores(
    purchase_price: Decimal | None,
    value_mid: Decimal | None,
    publisher_tier: str | None,
    year_start: int | None,
    is_complete: bool,
    condition_grade: str | None,
    author_priority_score: int,
    author_book_count: int,
    is_duplicate: bool,
    completes_set: bool,
    volume_count: int,
) -> dict[str, int]:
    """
    Calculate all score components for a book.

    Returns:
        Dict with investment_grade, strategic_fit, collection_impact, overall_score
    """
    investment = calculate_investment_grade(purchase_price, value_mid)
    strategic = calculate_strategic_fit(
        publisher_tier, year_start, is_complete, condition_grade, author_priority_score
    )
    collection = calculate_collection_impact(
        author_book_count, is_duplicate, completes_set, volume_count
    )

    return {
        "investment_grade": investment,
        "strategic_fit": strategic,
        "collection_impact": collection,
        "overall_score": investment + strategic + collection,
    }
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scoring.py::TestCalculateAllScores -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat: add calculate_all_scores function"
```

---

## Task 7: Add Score Calculation API Endpoint

**Files:**

- Modify: `backend/app/api/v1/books.py`
- Create: `backend/tests/test_scores_api.py`

### Step 1: Write the failing test

Create `backend/tests/test_scores_api.py`:

```python
"""Tests for score calculation API endpoints."""

import pytest
from decimal import Decimal


class TestCalculateScoresEndpoint:
    """Tests for POST /books/{id}/scores/calculate endpoint."""

    def test_calculate_scores_returns_scores(self, client, db):
        """Should return calculated scores for a book."""
        from app.models.book import Book
        from app.models.author import Author
        from app.models.publisher import Publisher

        # Create test data
        author = Author(name="George Eliot", priority_score=0)
        publisher = Publisher(name="Blackwood", tier="TIER_1")
        db.add_all([author, publisher])
        db.commit()

        book = Book(
            title="Middlemarch",
            author_id=author.id,
            publisher_id=publisher.id,
            year_start=1871,
            volumes=1,
            condition_grade="Very Good",
            purchase_price=Decimal("300"),
            value_mid=Decimal("1000"),
            status="EVALUATING",
        )
        db.add(book)
        db.commit()

        response = client.post(f"/api/v1/books/{book.id}/scores/calculate")

        assert response.status_code == 200
        data = response.json()
        assert "investment_grade" in data
        assert "strategic_fit" in data
        assert "collection_impact" in data
        assert "overall_score" in data
        assert data["investment_grade"] == 100  # 70% discount

    def test_calculate_scores_persists_to_db(self, client, db):
        """Scores should be persisted to database."""
        from app.models.book import Book

        book = Book(
            title="Test Book",
            purchase_price=Decimal("500"),
            value_mid=Decimal("1000"),
            status="EVALUATING",
        )
        db.add(book)
        db.commit()
        book_id = book.id

        client.post(f"/api/v1/books/{book_id}/scores/calculate")

        db.expire_all()
        updated_book = db.get(Book, book_id)
        assert updated_book.investment_grade is not None
        assert updated_book.overall_score is not None
        assert updated_book.scores_calculated_at is not None

    def test_calculate_scores_404_for_missing_book(self, client):
        """Should return 404 for non-existent book."""
        response = client.post("/api/v1/books/99999/scores/calculate")
        assert response.status_code == 404
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scores_api.py -v
```

Expected: FAIL with 404 (endpoint doesn't exist)

### Step 3: Add score calculation endpoint

Add to `backend/app/api/v1/books.py` (after existing endpoints, before the router is closed):

```python
from datetime import datetime
from app.services.scoring import calculate_all_scores, is_duplicate_title


@router.post("/{book_id}/scores/calculate")
def calculate_book_scores(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Calculate and persist scores for a book."""
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get related data for scoring
    author_priority = 0
    publisher_tier = None
    author_book_count = 0

    if book.author:
        author_priority = book.author.priority_score or 0
        # Count other books by this author (excluding current book)
        author_book_count = (
            db.query(Book)
            .filter(Book.author_id == book.author_id, Book.id != book.id)
            .count()
        )

    if book.publisher:
        publisher_tier = book.publisher.tier

    # Check for duplicate titles by same author
    is_duplicate = False
    if book.author_id:
        other_books = (
            db.query(Book)
            .filter(Book.author_id == book.author_id, Book.id != book.id)
            .all()
        )
        for other in other_books:
            if is_duplicate_title(book.title, other.title):
                is_duplicate = True
                break

    # Calculate scores
    scores = calculate_all_scores(
        purchase_price=book.purchase_price,
        value_mid=book.value_mid,
        publisher_tier=publisher_tier,
        year_start=book.year_start,
        is_complete=(book.volumes == 1 or book.volumes is None),  # Single vol = complete
        condition_grade=book.condition_grade,
        author_priority_score=author_priority,
        author_book_count=author_book_count,
        is_duplicate=is_duplicate,
        completes_set=False,  # TODO: detect incomplete sets
        volume_count=book.volumes or 1,
    )

    # Persist scores
    book.investment_grade = scores["investment_grade"]
    book.strategic_fit = scores["strategic_fit"]
    book.collection_impact = scores["collection_impact"]
    book.overall_score = scores["overall_score"]
    book.scores_calculated_at = datetime.utcnow()

    db.commit()
    db.refresh(book)

    return scores
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scores_api.py -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/test_scores_api.py
git commit -m "feat: add POST /books/{id}/scores/calculate endpoint"
```

---

## Task 8: Auto-Calculate Scores on Book Creation

**Files:**

- Modify: `backend/app/api/v1/books.py`
- Modify: `backend/tests/test_scores_api.py`

### Step 1: Write the failing test

Add to `backend/tests/test_scores_api.py`:

```python
class TestAutoScoreOnCreate:
    """Tests for automatic score calculation on book creation."""

    def test_scores_calculated_on_create(self, client, db):
        """Creating a book should auto-calculate scores."""
        from app.models.author import Author
        from app.models.publisher import Publisher

        author = Author(name="Test Author")
        publisher = Publisher(name="Test Publisher", tier="TIER_1")
        db.add_all([author, publisher])
        db.commit()

        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "author_id": author.id,
                "publisher_id": publisher.id,
                "year_start": 1867,
                "purchase_price": 300,
                "value_mid": 1000,
                "status": "EVALUATING",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["investment_grade"] is not None
        assert data["strategic_fit"] is not None
        assert data["overall_score"] is not None
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scores_api.py::TestAutoScoreOnCreate -v
```

Expected: FAIL (scores are None)

### Step 3: Add auto-calculation to create endpoint

Find the `create_book` function in `backend/app/api/v1/books.py` and add score calculation after `db.commit()` but before the return.

Add this helper function near the top of the file (after imports):

```python
def _calculate_and_persist_scores(book: Book, db: Session) -> None:
    """Calculate and persist scores for a book."""
    author_priority = 0
    publisher_tier = None
    author_book_count = 0

    if book.author:
        author_priority = book.author.priority_score or 0
        author_book_count = (
            db.query(Book)
            .filter(Book.author_id == book.author_id, Book.id != book.id)
            .count()
        )

    if book.publisher:
        publisher_tier = book.publisher.tier

    is_duplicate = False
    if book.author_id:
        other_books = (
            db.query(Book)
            .filter(Book.author_id == book.author_id, Book.id != book.id)
            .all()
        )
        for other in other_books:
            if is_duplicate_title(book.title, other.title):
                is_duplicate = True
                break

    scores = calculate_all_scores(
        purchase_price=book.purchase_price,
        value_mid=book.value_mid,
        publisher_tier=publisher_tier,
        year_start=book.year_start,
        is_complete=(book.volumes == 1 or book.volumes is None),
        condition_grade=book.condition_grade,
        author_priority_score=author_priority,
        author_book_count=author_book_count,
        is_duplicate=is_duplicate,
        completes_set=False,
        volume_count=book.volumes or 1,
    )

    book.investment_grade = scores["investment_grade"]
    book.strategic_fit = scores["strategic_fit"]
    book.collection_impact = scores["collection_impact"]
    book.overall_score = scores["overall_score"]
    book.scores_calculated_at = datetime.utcnow()
```

Then in `create_book`, after `db.commit()` and before `db.refresh(book)`:

```python
    # Auto-calculate scores
    _calculate_and_persist_scores(book, db)
    db.commit()
```

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scores_api.py::TestAutoScoreOnCreate -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/test_scores_api.py
git commit -m "feat: auto-calculate scores on book creation"
```

---

## Task 9: Add Scores to Book Response Schema

**Files:**

- Modify: `backend/app/api/v1/books.py` (or schemas file if separate)
- Verify existing tests pass

### Step 1: Verify scores are included in responses

Check that the Book response model includes score fields. If using Pydantic models, add:

```python
class BookResponse(BaseModel):
    # ... existing fields ...
    investment_grade: int | None = None
    strategic_fit: int | None = None
    collection_impact: int | None = None
    overall_score: int | None = None
    scores_calculated_at: datetime | None = None
```

### Step 2: Run all tests

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
```

Expected: All PASS

### Step 3: Commit

```bash
git add backend/
git commit -m "feat: include scores in book response schema"
```

---

## Task 10: Add Frontend Score Display Types

**Files:**

- Modify: `frontend/src/stores/acquisitions.ts`
- Modify: `frontend/src/stores/books.ts`

### Step 1: Add score fields to TypeScript interfaces

In `frontend/src/stores/acquisitions.ts`, update the `AcquisitionBook` interface:

```typescript
export interface AcquisitionBook {
  // ... existing fields ...
  investment_grade?: number | null;
  strategic_fit?: number | null;
  collection_impact?: number | null;
  overall_score?: number | null;
  scores_calculated_at?: string | null;
}
```

In `frontend/src/stores/books.ts`, update the Book interface similarly.

### Step 2: Add calculateScores action to books store

In `frontend/src/stores/books.ts`:

```typescript
async calculateScores(bookId: number) {
  const response = await api.post(`/books/${bookId}/scores/calculate`);
  return response.data;
}
```

### Step 3: Run type check

```bash
cd frontend && npm run type-check
```

Expected: PASS

### Step 4: Commit

```bash
git add frontend/src/stores/
git commit -m "feat: add score types and calculateScores action to frontend"
```

---

## Task 11: Add Score Display Component

**Files:**

- Create: `frontend/src/components/ScoreCard.vue`

### Step 1: Create ScoreCard component

Create `frontend/src/components/ScoreCard.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";

interface Props {
  investmentGrade?: number | null;
  strategicFit?: number | null;
  collectionImpact?: number | null;
  overallScore?: number | null;
  compact?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
});

const scoreLabel = computed(() => {
  const score = props.overallScore;
  if (score === null || score === undefined) return "N/A";
  if (score >= 160) return "STRONG BUY";
  if (score >= 120) return "BUY";
  if (score >= 80) return "CONDITIONAL";
  return "PASS";
});

const scoreColor = computed(() => {
  const score = props.overallScore;
  if (score === null || score === undefined) return "bg-gray-200 text-gray-600";
  if (score >= 160) return "bg-green-500 text-white";
  if (score >= 120) return "bg-yellow-500 text-white";
  if (score >= 80) return "bg-orange-500 text-white";
  return "bg-red-500 text-white";
});

function formatScore(score?: number | null): string {
  if (score === null || score === undefined) return "-";
  return score.toString();
}
</script>

<template>
  <div v-if="compact" class="flex items-center gap-2">
    <span
      :class="[scoreColor, 'px-2 py-1 rounded text-xs font-bold']"
    >
      {{ formatScore(overallScore) }}
    </span>
  </div>

  <div v-else class="border rounded-lg p-3 bg-white">
    <!-- Overall Score Header -->
    <div class="flex items-center justify-between mb-3">
      <span class="text-sm font-medium text-gray-600">SCORE</span>
      <span :class="[scoreColor, 'px-3 py-1 rounded font-bold text-sm']">
        {{ formatScore(overallScore) }} {{ scoreLabel }}
      </span>
    </div>

    <!-- Component Breakdown -->
    <div class="space-y-2 text-sm">
      <div class="flex justify-between items-center">
        <span class="text-gray-600">Investment</span>
        <div class="flex items-center gap-2">
          <div class="w-20 bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-500 h-2 rounded-full"
              :style="{ width: `${Math.min((investmentGrade || 0), 100)}%` }"
            ></div>
          </div>
          <span class="w-8 text-right font-medium">{{ formatScore(investmentGrade) }}</span>
        </div>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-gray-600">Strategic</span>
        <div class="flex items-center gap-2">
          <div class="w-20 bg-gray-200 rounded-full h-2">
            <div
              class="bg-purple-500 h-2 rounded-full"
              :style="{ width: `${Math.min((strategicFit || 0), 100)}%` }"
            ></div>
          </div>
          <span class="w-8 text-right font-medium">{{ formatScore(strategicFit) }}</span>
        </div>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-gray-600">Collection</span>
        <div class="flex items-center gap-2">
          <div class="w-20 bg-gray-200 rounded-full h-2">
            <div
              class="bg-teal-500 h-2 rounded-full"
              :style="{ width: `${Math.max(0, Math.min((collectionImpact || 0), 100))}%` }"
            ></div>
          </div>
          <span class="w-8 text-right font-medium">{{ formatScore(collectionImpact) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
```

### Step 2: Run build to verify no errors

```bash
cd frontend && npm run build
```

Expected: Success

### Step 3: Commit

```bash
git add frontend/src/components/ScoreCard.vue
git commit -m "feat: add ScoreCard component for score display"
```

---

## Task 12: Integrate ScoreCard into AcquisitionsView

**Files:**

- Modify: `frontend/src/views/AcquisitionsView.vue`

### Step 1: Import and use ScoreCard

Add to imports:

```typescript
import ScoreCard from "@/components/ScoreCard.vue";
```

Add recalculate handler:

```typescript
const recalculatingScore = ref<number | null>(null);

async function handleRecalculateScore(bookId: number) {
  if (recalculatingScore.value) return;
  recalculatingScore.value = bookId;
  try {
    await booksStore.calculateScores(bookId);
    await acquisitionsStore.fetchAll();
  } finally {
    recalculatingScore.value = null;
  }
}
```

### Step 2: Add ScoreCard to EVALUATING cards

In the template, add the ScoreCard component to EVALUATING column cards:

```vue
<!-- Inside EVALUATING card, after price info -->
<ScoreCard
  :investment-grade="item.investment_grade"
  :strategic-fit="item.strategic_fit"
  :collection-impact="item.collection_impact"
  :overall-score="item.overall_score"
/>

<!-- Recalculate button -->
<button
  @click="handleRecalculateScore(item.id)"
  :disabled="recalculatingScore === item.id"
  class="text-xs text-blue-600 hover:text-blue-800"
>
  {{ recalculatingScore === item.id ? "..." : "Recalc" }}
</button>
```

For IN_TRANSIT and ON_HAND columns, use compact mode:

```vue
<ScoreCard
  :overall-score="item.overall_score"
  compact
/>
```

### Step 3: Run type check and build

```bash
cd frontend && npm run type-check && npm run build
```

Expected: Success

### Step 4: Commit

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat: integrate ScoreCard into AcquisitionsView"
```

---

## Task 13: Add Batch Calculate Scores Endpoint

**Files:**

- Modify: `backend/app/api/v1/books.py`
- Modify: `backend/tests/test_scores_api.py`

### Step 1: Write the failing test

Add to `backend/tests/test_scores_api.py`:

```python
class TestBatchCalculateScores:
    """Tests for POST /books/scores/calculate-all endpoint."""

    def test_batch_calculate_updates_all_books(self, client, db):
        """Should update scores for all books."""
        from app.models.book import Book

        # Create test books
        for i in range(3):
            book = Book(
                title=f"Test Book {i}",
                purchase_price=Decimal("500"),
                value_mid=Decimal("1000"),
            )
            db.add(book)
        db.commit()

        response = client.post("/api/v1/books/scores/calculate-all")

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 3
        assert len(data["errors"]) == 0
```

### Step 2: Run test to verify it fails

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scores_api.py::TestBatchCalculateScores -v
```

Expected: FAIL with 404

### Step 3: Add batch endpoint

Add to `backend/app/api/v1/books.py`:

```python
@router.post("/scores/calculate-all")
def calculate_all_book_scores(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Calculate scores for all books. Admin only."""
    books = db.query(Book).all()
    updated = 0
    errors = []

    for book in books:
        try:
            _calculate_and_persist_scores(book, db)
            updated += 1
        except Exception as e:
            errors.append({"book_id": book.id, "error": str(e)})

    db.commit()

    return {"updated_count": updated, "errors": errors}
```

**Note:** Place this endpoint BEFORE the `/{book_id}` routes to avoid path conflicts.

### Step 4: Run test to verify it passes

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_scores_api.py::TestBatchCalculateScores -v
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/test_scores_api.py
git commit -m "feat: add POST /books/scores/calculate-all batch endpoint"
```

---

## Task 14: Database Migration (Manual Step)

**Note:** This task requires running Alembic migration commands against the database.

### Step 1: Generate migration

```bash
cd backend && source .venv/bin/activate
alembic revision --autogenerate -m "add scoring fields"
```

### Step 2: Review generated migration

Check `backend/alembic/versions/<timestamp>_add_scoring_fields.py` contains:

- `priority_score` column on `authors` table
- `investment_grade`, `strategic_fit`, `collection_impact`, `overall_score`, `scores_calculated_at` columns on `books` table

### Step 3: Apply migration to staging

```bash
# Export database URL and run
alembic upgrade head
```

### Step 4: Backfill scores

Use the batch endpoint to calculate scores for existing books:

```bash
bmx-api POST /books/scores/calculate-all
```

### Step 5: Commit migration file

```bash
git add backend/alembic/versions/
git commit -m "migration: add scoring fields to books and authors"
```

---

## Task 15: Set Initial Author Priority Scores

**Files:**

- Create: `backend/scripts/seed_author_priorities.py`

### Step 1: Create seed script

Create `backend/scripts/seed_author_priorities.py`:

```python
"""Seed author priority scores based on acquisition protocol."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.author import Author

AUTHOR_PRIORITIES = {
    "Thomas Hardy": 50,
    "Charles Darwin": 50,
    "Charles Lyell": 40,
    "James Clerk Maxwell": 40,
    "Charles Dickens": 30,
    "Thomas Carlyle": 25,
    "John Ruskin": 25,
    "Wilkie Collins": 20,
}


def seed_priorities():
    db = SessionLocal()
    try:
        for name, score in AUTHOR_PRIORITIES.items():
            author = db.query(Author).filter(Author.name.ilike(f"%{name}%")).first()
            if author:
                author.priority_score = score
                print(f"Updated {author.name}: {score}")
            else:
                print(f"Not found: {name}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_priorities()
```

### Step 2: Run seed script

```bash
cd backend && source .venv/bin/activate && python scripts/seed_author_priorities.py
```

### Step 3: Commit

```bash
git add backend/scripts/seed_author_priorities.py
git commit -m "feat: add script to seed author priority scores"
```

---

## Task 16: Final Integration Test and Lint

### Step 1: Run all backend tests

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
```

Expected: All PASS

### Step 2: Run backend lint

```bash
cd backend && source .venv/bin/activate && ruff check --fix . && ruff format .
```

### Step 3: Run frontend checks

```bash
cd frontend && npm run type-check && npm run build && npx prettier --write "src/**/*.{ts,vue}"
```

### Step 4: Final commit

```bash
git add .
git commit -m "chore: lint and format scoring engine implementation"
```

### Step 5: Push to staging

```bash
git push origin staging
```

---

## Summary

16 tasks implementing:

1. Author `priority_score` field
2. Book score fields (4 new columns)
3. Investment grade calculator
4. Strategic fit calculator
5. Collection impact calculator with duplicate detection
6. Combined score calculation function
7. Score calculation API endpoint
8. Auto-calculate on book creation
9. Scores in API response schema
10. Frontend TypeScript types
11. ScoreCard Vue component
12. Integration into AcquisitionsView
13. Batch calculate endpoint
14. Database migration
15. Author priority seed script
16. Final integration test
