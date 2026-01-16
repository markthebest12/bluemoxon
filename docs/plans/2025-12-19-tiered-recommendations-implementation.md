# Tiered Recommendations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform eval runbook from binary ACQUIRE/PASS to tiered recommendations (STRONG_BUY/BUY/CONDITIONAL/PASS) with suggested offer prices and reasoning.

**Architecture:** New scoring functions calculate Quality Score (0-100) and Strategic Fit Score (0-100) separately, combined with weighted average. Recommendation matrix with floor rules determines tier. Templated reasoning provides explanation.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic, Pydantic, Vue 3, TypeScript

**Design Doc:** `docs/plans/2025-12-19-tiered-recommendations-design.md`

---

## Phase 1: Quality Score Engine

### Task 1.1: Create Quality Score Tests

**Files:**

- Create: `backend/tests/test_tiered_scoring.py`

**Step 1: Write the failing tests**

```python
"""Tests for tiered recommendation scoring."""

from decimal import Decimal

import pytest


class TestQualityScore:
    """Tests for quality score calculation (0-100)."""

    def test_tier_1_publisher_adds_25(self):
        """Tier 1 publisher should add 25 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 25

    def test_tier_2_publisher_adds_10(self):
        """Tier 2 publisher should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_2",
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 10

    def test_tier_1_binder_adds_30(self):
        """Tier 1 binder should add 30 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier="TIER_1",
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 30

    def test_tier_2_binder_adds_15(self):
        """Tier 2 binder should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier="TIER_2",
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_double_tier_1_bonus_adds_10(self):
        """Both publisher AND binder Tier 1 should add bonus 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier="TIER_1",  # +30 + 10 bonus
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 65  # 25 + 30 + 10

    def test_victorian_era_adds_15(self):
        """Victorian era (1837-1901) should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=1867,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_romantic_era_adds_15(self):
        """Romantic era (1800-1836) should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=1820,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_fine_condition_adds_15(self):
        """Fine/VG+ condition should add 15 points."""
        from app.services.tiered_scoring import calculate_quality_score

        for grade in ["Fine", "VG+"]:
            score = calculate_quality_score(
                publisher_tier=None,
                binder_tier=None,
                year_start=None,
                condition_grade=grade,
                is_complete=False,
                author_priority_score=0,
                volume_count=1,
                is_duplicate=False,
            )
            assert score == 15, f"Failed for grade: {grade}"

    def test_good_condition_adds_10(self):
        """Good condition should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        for grade in ["Good", "VG", "Very Good", "Good+"]:
            score = calculate_quality_score(
                publisher_tier=None,
                binder_tier=None,
                year_start=None,
                condition_grade=grade,
                is_complete=False,
                author_priority_score=0,
                volume_count=1,
                is_duplicate=False,
            )
            assert score == 10, f"Failed for grade: {grade}"

    def test_complete_set_adds_10(self):
        """Complete set should add 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=True,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 10

    def test_author_priority_capped_at_15(self):
        """Author priority score should be capped at 15."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=50,  # Should cap at 15
            volume_count=1,
            is_duplicate=False,
        )
        assert score == 15

    def test_duplicate_penalty_minus_30(self):
        """Duplicate title should subtract 30 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=True,  # -30
        )
        assert score == 0  # 25 - 30 = -5, floored at 0

    def test_large_volume_penalty_minus_10(self):
        """5+ volumes should subtract 10 points."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=6,  # -10
            is_duplicate=False,
        )
        assert score == 15  # 25 - 10

    def test_max_quality_score_is_100(self):
        """Quality score should cap at 100."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier="TIER_1",  # +25
            binder_tier="TIER_1",  # +30 + 10 bonus = 40
            year_start=1867,  # +15
            condition_grade="Fine",  # +15
            is_complete=True,  # +10
            author_priority_score=50,  # +15 (capped)
            volume_count=1,
            is_duplicate=False,
        )
        # 25 + 40 + 15 + 15 + 10 + 15 = 120, capped at 100
        assert score == 100

    def test_quality_score_floors_at_zero(self):
        """Quality score should not go below 0."""
        from app.services.tiered_scoring import calculate_quality_score

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=True,  # -30
        )
        assert score == 0
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.tiered_scoring'"

**Step 3: Commit test file**

```bash
git add backend/tests/test_tiered_scoring.py
git commit -m "test: add quality score tests for tiered recommendations #388"
```

---

### Task 1.2: Implement Quality Score Function

**Files:**

- Create: `backend/app/services/tiered_scoring.py`

**Step 1: Write minimal implementation**

```python
"""Tiered recommendation scoring engine.

This module calculates Quality Score and Strategic Fit Score for the
tiered recommendation system (STRONG_BUY/BUY/CONDITIONAL/PASS).

See docs/plans/2025-12-19-tiered-recommendations-design.md for full design.
"""

from __future__ import annotations

# Quality score point values
QUALITY_TIER_1_PUBLISHER = 25
QUALITY_TIER_2_PUBLISHER = 10
QUALITY_TIER_1_BINDER = 30
QUALITY_TIER_2_BINDER = 15
QUALITY_DOUBLE_TIER_1_BONUS = 10
QUALITY_ERA_BONUS = 15
QUALITY_CONDITION_FINE = 15
QUALITY_CONDITION_GOOD = 10
QUALITY_COMPLETE_SET = 10
QUALITY_AUTHOR_PRIORITY_CAP = 15
QUALITY_DUPLICATE_PENALTY = -30
QUALITY_LARGE_VOLUME_PENALTY = -10

# Era boundaries
ROMANTIC_START = 1800
ROMANTIC_END = 1836
VICTORIAN_START = 1837
VICTORIAN_END = 1901

# Condition grades
FINE_CONDITIONS = {"Fine", "VG+"}
GOOD_CONDITIONS = {"Good", "VG", "Very Good", "Good+", "VG-"}


def calculate_quality_score(
    publisher_tier: str | None,
    binder_tier: str | None,
    year_start: int | None,
    condition_grade: str | None,
    is_complete: bool,
    author_priority_score: int,
    volume_count: int,
    is_duplicate: bool,
) -> int:
    """Calculate quality score (0-100) measuring intrinsic book desirability.

    This score is independent of price - it measures whether the book is
    worth acquiring at the right price.

    Args:
        publisher_tier: TIER_1, TIER_2, or None
        binder_tier: TIER_1, TIER_2, or None
        year_start: Publication year
        condition_grade: Condition grade string
        is_complete: Whether set is complete
        author_priority_score: Priority score from author record
        volume_count: Number of volumes
        is_duplicate: Whether title already in collection

    Returns:
        Quality score 0-100
    """
    score = 0

    # Publisher tier
    if publisher_tier == "TIER_1":
        score += QUALITY_TIER_1_PUBLISHER
    elif publisher_tier == "TIER_2":
        score += QUALITY_TIER_2_PUBLISHER

    # Binder tier
    if binder_tier == "TIER_1":
        score += QUALITY_TIER_1_BINDER
    elif binder_tier == "TIER_2":
        score += QUALITY_TIER_2_BINDER

    # Double Tier 1 bonus
    if publisher_tier == "TIER_1" and binder_tier == "TIER_1":
        score += QUALITY_DOUBLE_TIER_1_BONUS

    # Era bonus (Victorian or Romantic)
    if year_start is not None:
        if ROMANTIC_START <= year_start <= VICTORIAN_END:
            score += QUALITY_ERA_BONUS

    # Condition bonus
    if condition_grade:
        if condition_grade in FINE_CONDITIONS:
            score += QUALITY_CONDITION_FINE
        elif condition_grade in GOOD_CONDITIONS:
            score += QUALITY_CONDITION_GOOD

    # Complete set bonus
    if is_complete:
        score += QUALITY_COMPLETE_SET

    # Author priority (capped)
    score += min(author_priority_score, QUALITY_AUTHOR_PRIORITY_CAP)

    # Penalties
    if is_duplicate:
        score += QUALITY_DUPLICATE_PENALTY

    if volume_count >= 5:
        score += QUALITY_LARGE_VOLUME_PENALTY

    # Floor at 0, cap at 100
    return max(0, min(100, score))
```

**Step 2: Run tests to verify they pass**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestQualityScore -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add backend/app/services/tiered_scoring.py
git commit -m "feat: add calculate_quality_score function #388"
```

---

### Task 1.3: Add Strategic Fit Score Tests

**Files:**

- Modify: `backend/tests/test_tiered_scoring.py`

**Step 1: Add strategic fit tests to test file**

```python
class TestStrategicFitScore:
    """Tests for strategic fit score calculation (0-100)."""

    def test_publisher_matches_author_requirement_adds_40(self):
        """Right publisher for author should add 40 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=True,
            author_book_count=5,
            completes_set=False,
        )
        assert score == 40

    def test_new_author_adds_30(self):
        """New author to collection should add 30 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=0,
            completes_set=False,
        )
        assert score == 30

    def test_second_author_work_adds_15(self):
        """Second work by author should add 15 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=1,
            completes_set=False,
        )
        assert score == 15

    def test_completes_set_adds_25(self):
        """Completing a set should add 25 points."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=5,
            completes_set=True,
        )
        assert score == 25

    def test_combined_strategic_factors(self):
        """All strategic factors should combine."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=True,  # +40
            author_book_count=0,  # +30
            completes_set=True,  # +25
        )
        assert score == 95  # 40 + 30 + 25

    def test_strategic_fit_caps_at_100(self):
        """Strategic fit should cap at 100."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        # Even with maximum factors, cap at 100
        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=True,  # +40
            author_book_count=0,  # +30
            completes_set=True,  # +25
        )
        assert score <= 100

    def test_strategic_fit_floors_at_zero(self):
        """Strategic fit should not go below 0."""
        from app.services.tiered_scoring import calculate_strategic_fit_score

        score = calculate_strategic_fit_score(
            publisher_matches_author_requirement=False,
            author_book_count=10,  # No bonus
            completes_set=False,
        )
        assert score == 0
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestStrategicFitScore -v`
Expected: FAIL with "cannot import name 'calculate_strategic_fit_score'"

**Step 3: Commit test additions**

```bash
git add backend/tests/test_tiered_scoring.py
git commit -m "test: add strategic fit score tests #388"
```

---

### Task 1.4: Implement Strategic Fit Score Function

**Files:**

- Modify: `backend/app/services/tiered_scoring.py`

**Step 1: Add strategic fit function**

Add after the quality score function:

```python
# Strategic fit point values
STRATEGIC_PUBLISHER_MATCH = 40
STRATEGIC_NEW_AUTHOR = 30
STRATEGIC_SECOND_WORK = 15
STRATEGIC_COMPLETES_SET = 25


def calculate_strategic_fit_score(
    publisher_matches_author_requirement: bool,
    author_book_count: int,
    completes_set: bool,
) -> int:
    """Calculate strategic fit score (0-100) measuring collection alignment.

    This score measures how well the book fits the collection strategy,
    independent of intrinsic quality or price.

    Args:
        publisher_matches_author_requirement: True if publisher matches
            the required publisher for this author (e.g., Collins → Bentley)
        author_book_count: Number of books by this author already in collection
        completes_set: True if this book completes an incomplete set

    Returns:
        Strategic fit score 0-100
    """
    score = 0

    # Publisher matches author requirement (e.g., Collins + Bentley)
    if publisher_matches_author_requirement:
        score += STRATEGIC_PUBLISHER_MATCH

    # Author presence bonus
    if author_book_count == 0:
        score += STRATEGIC_NEW_AUTHOR
    elif author_book_count == 1:
        score += STRATEGIC_SECOND_WORK

    # Set completion bonus
    if completes_set:
        score += STRATEGIC_COMPLETES_SET

    # Floor at 0, cap at 100
    return max(0, min(100, score))
```

**Step 2: Run tests to verify they pass**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestStrategicFitScore -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add backend/app/services/tiered_scoring.py
git commit -m "feat: add calculate_strategic_fit_score function #388"
```

---

## Phase 2: Recommendation Matrix

### Task 2.1: Add Price Position and Combined Score Tests

**Files:**

- Modify: `backend/tests/test_tiered_scoring.py`

**Step 1: Add tests**

```python
from decimal import Decimal


class TestPricePosition:
    """Tests for price position calculation."""

    def test_excellent_price_under_70_percent(self):
        """Price < 70% FMV should be EXCELLENT."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("60"),
            fmv_mid=Decimal("100"),
        )
        assert position == "EXCELLENT"

    def test_good_price_70_to_85_percent(self):
        """Price 70-85% FMV should be GOOD."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("75"),
            fmv_mid=Decimal("100"),
        )
        assert position == "GOOD"

    def test_fair_price_85_to_100_percent(self):
        """Price 85-100% FMV should be FAIR."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("95"),
            fmv_mid=Decimal("100"),
        )
        assert position == "FAIR"

    def test_poor_price_over_100_percent(self):
        """Price > 100% FMV should be POOR."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("120"),
            fmv_mid=Decimal("100"),
        )
        assert position == "POOR"

    def test_no_fmv_returns_none(self):
        """Missing FMV should return None."""
        from app.services.tiered_scoring import calculate_price_position

        position = calculate_price_position(
            asking_price=Decimal("100"),
            fmv_mid=None,
        )
        assert position is None


class TestCombinedScore:
    """Tests for combined score calculation."""

    def test_combined_score_weights(self):
        """Combined score should weight quality 60%, strategic fit 40%."""
        from app.services.tiered_scoring import calculate_combined_score

        combined = calculate_combined_score(
            quality_score=100,
            strategic_fit_score=0,
        )
        assert combined == 60  # 100 * 0.6 + 0 * 0.4

        combined = calculate_combined_score(
            quality_score=0,
            strategic_fit_score=100,
        )
        assert combined == 40  # 0 * 0.6 + 100 * 0.4

    def test_combined_score_balanced(self):
        """Balanced scores should average correctly."""
        from app.services.tiered_scoring import calculate_combined_score

        combined = calculate_combined_score(
            quality_score=80,
            strategic_fit_score=80,
        )
        assert combined == 80  # 80 * 0.6 + 80 * 0.4
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestPricePosition -v`
Expected: FAIL

**Step 3: Commit**

```bash
git add backend/tests/test_tiered_scoring.py
git commit -m "test: add price position and combined score tests #388"
```

---

### Task 2.2: Implement Price Position and Combined Score

**Files:**

- Modify: `backend/app/services/tiered_scoring.py`

**Step 1: Add functions**

```python
from decimal import Decimal

# Price position thresholds
PRICE_EXCELLENT_THRESHOLD = Decimal("0.70")  # < 70% of FMV
PRICE_GOOD_THRESHOLD = Decimal("0.85")  # 70-85% of FMV
PRICE_FAIR_THRESHOLD = Decimal("1.00")  # 85-100% of FMV

# Combined score weights
QUALITY_WEIGHT = 0.6
STRATEGIC_FIT_WEIGHT = 0.4


def calculate_price_position(
    asking_price: Decimal | None,
    fmv_mid: Decimal | None,
) -> str | None:
    """Determine price position relative to FMV.

    Args:
        asking_price: Current asking price
        fmv_mid: Midpoint of FMV range

    Returns:
        EXCELLENT, GOOD, FAIR, POOR, or None if FMV unknown
    """
    if fmv_mid is None or asking_price is None or fmv_mid <= 0:
        return None

    ratio = asking_price / fmv_mid

    if ratio < PRICE_EXCELLENT_THRESHOLD:
        return "EXCELLENT"
    elif ratio < PRICE_GOOD_THRESHOLD:
        return "GOOD"
    elif ratio <= PRICE_FAIR_THRESHOLD:
        return "FAIR"
    else:
        return "POOR"


def calculate_combined_score(
    quality_score: int,
    strategic_fit_score: int,
) -> int:
    """Calculate combined score with weighted average.

    Args:
        quality_score: Quality score (0-100)
        strategic_fit_score: Strategic fit score (0-100)

    Returns:
        Combined score (0-100)
    """
    combined = (quality_score * QUALITY_WEIGHT) + (strategic_fit_score * STRATEGIC_FIT_WEIGHT)
    return int(round(combined))
```

**Step 2: Run tests**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestPricePosition backend/tests/test_tiered_scoring.py::TestCombinedScore -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/app/services/tiered_scoring.py
git commit -m "feat: add price position and combined score functions #388"
```

---

### Task 2.3: Add Recommendation Matrix Tests

**Files:**

- Modify: `backend/tests/test_tiered_scoring.py`

**Step 1: Add matrix tests**

```python
class TestRecommendationMatrix:
    """Tests for recommendation matrix with floor rules."""

    def test_high_score_excellent_price_strong_buy(self):
        """Score >= 80 + EXCELLENT price = STRONG_BUY."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=85,
            price_position="EXCELLENT",
            quality_score=80,
            strategic_fit_score=80,
        )
        assert tier == "STRONG_BUY"

    def test_high_score_poor_price_conditional(self):
        """Score >= 80 + POOR price = CONDITIONAL."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=85,
            price_position="POOR",
            quality_score=80,
            strategic_fit_score=80,
        )
        assert tier == "CONDITIONAL"

    def test_low_score_excellent_price_buy(self):
        """Score 40-59 + EXCELLENT price = BUY."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=50,
            price_position="EXCELLENT",
            quality_score=50,
            strategic_fit_score=50,
        )
        assert tier == "BUY"

    def test_low_score_fair_price_pass(self):
        """Score 40-59 + FAIR price = PASS."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=50,
            price_position="FAIR",
            quality_score=50,
            strategic_fit_score=50,
        )
        assert tier == "PASS"

    def test_strategic_fit_floor_caps_at_conditional(self):
        """Strategic fit < 30 should cap at CONDITIONAL regardless of matrix."""
        from app.services.tiered_scoring import determine_recommendation_tier

        # Would be STRONG_BUY without floor
        tier = determine_recommendation_tier(
            combined_score=85,
            price_position="EXCELLENT",
            quality_score=100,
            strategic_fit_score=20,  # Below 30 floor
        )
        assert tier == "CONDITIONAL"

    def test_quality_floor_caps_at_conditional(self):
        """Quality < 40 should cap at CONDITIONAL regardless of matrix."""
        from app.services.tiered_scoring import determine_recommendation_tier

        # Would be BUY without floor
        tier = determine_recommendation_tier(
            combined_score=60,
            price_position="EXCELLENT",
            quality_score=30,  # Below 40 floor
            strategic_fit_score=100,
        )
        assert tier == "CONDITIONAL"

    def test_no_price_position_uses_fair(self):
        """Missing price position should default to FAIR behavior."""
        from app.services.tiered_scoring import determine_recommendation_tier

        tier = determine_recommendation_tier(
            combined_score=75,
            price_position=None,
            quality_score=75,
            strategic_fit_score=75,
        )
        assert tier == "CONDITIONAL"  # 60-79 + FAIR = CONDITIONAL
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestRecommendationMatrix -v`
Expected: FAIL

**Step 3: Commit**

```bash
git add backend/tests/test_tiered_scoring.py
git commit -m "test: add recommendation matrix tests with floor rules #388"
```

---

### Task 2.4: Implement Recommendation Matrix

**Files:**

- Modify: `backend/app/services/tiered_scoring.py`

**Step 1: Add matrix function**

```python
# Floor thresholds
STRATEGIC_FIT_FLOOR = 30
QUALITY_FLOOR = 40

# Recommendation tiers
STRONG_BUY = "STRONG_BUY"
BUY = "BUY"
CONDITIONAL = "CONDITIONAL"
PASS = "PASS"

# Recommendation matrix: (min_score, max_score) -> {price_position: tier}
RECOMMENDATION_MATRIX = {
    (80, 100): {
        "EXCELLENT": STRONG_BUY,
        "GOOD": STRONG_BUY,
        "FAIR": BUY,
        "POOR": CONDITIONAL,
    },
    (60, 79): {
        "EXCELLENT": STRONG_BUY,
        "GOOD": BUY,
        "FAIR": CONDITIONAL,
        "POOR": PASS,
    },
    (40, 59): {
        "EXCELLENT": BUY,
        "GOOD": CONDITIONAL,
        "FAIR": PASS,
        "POOR": PASS,
    },
    (0, 39): {
        "EXCELLENT": CONDITIONAL,
        "GOOD": PASS,
        "FAIR": PASS,
        "POOR": PASS,
    },
}


def determine_recommendation_tier(
    combined_score: int,
    price_position: str | None,
    quality_score: int,
    strategic_fit_score: int,
) -> str:
    """Determine recommendation tier from matrix with floor rules.

    Args:
        combined_score: Weighted combined score (0-100)
        price_position: EXCELLENT, GOOD, FAIR, POOR, or None
        quality_score: Quality score for floor check
        strategic_fit_score: Strategic fit score for floor check

    Returns:
        STRONG_BUY, BUY, CONDITIONAL, or PASS
    """
    # Default price position to FAIR if unknown
    effective_price = price_position or "FAIR"

    # Find the score range
    for (min_score, max_score), positions in RECOMMENDATION_MATRIX.items():
        if min_score <= combined_score <= max_score:
            tier = positions.get(effective_price, PASS)
            break
    else:
        tier = PASS

    # Apply floor rules - cap at CONDITIONAL if floors not met
    if strategic_fit_score < STRATEGIC_FIT_FLOOR:
        if tier in (STRONG_BUY, BUY):
            tier = CONDITIONAL

    if quality_score < QUALITY_FLOOR:
        if tier in (STRONG_BUY, BUY):
            tier = CONDITIONAL

    return tier
```

**Step 2: Run tests**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestRecommendationMatrix -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/app/services/tiered_scoring.py
git commit -m "feat: add recommendation matrix with floor rules #388"
```

---

## Phase 3: Offer Price and Reasoning

### Task 3.1: Add Suggested Offer Tests

**Files:**

- Modify: `backend/tests/test_tiered_scoring.py`

**Step 1: Add tests**

```python
class TestSuggestedOffer:
    """Tests for suggested offer price calculation."""

    def test_high_combined_score_15_percent_discount(self):
        """Score 70-79 should target 15% below FMV."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=75,
            fmv_mid=Decimal("100"),
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert offer == Decimal("85")  # 100 * 0.85

    def test_medium_combined_score_25_percent_discount(self):
        """Score 60-69 should target 25% below FMV."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=65,
            fmv_mid=Decimal("100"),
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert offer == Decimal("75")  # 100 * 0.75

    def test_strategic_floor_40_percent_discount(self):
        """Strategic floor triggered should use 40% discount."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=85,  # Would normally be 15%
            fmv_mid=Decimal("100"),
            strategic_floor_applied=True,
            quality_floor_applied=False,
        )
        assert offer == Decimal("60")  # 100 * 0.60

    def test_quality_floor_50_percent_discount(self):
        """Quality floor triggered should use 50% discount."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=70,
            fmv_mid=Decimal("100"),
            strategic_floor_applied=False,
            quality_floor_applied=True,
        )
        assert offer == Decimal("50")  # 100 * 0.50

    def test_no_fmv_returns_none(self):
        """Missing FMV should return None."""
        from app.services.tiered_scoring import calculate_suggested_offer

        offer = calculate_suggested_offer(
            combined_score=75,
            fmv_mid=None,
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert offer is None
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestSuggestedOffer -v`
Expected: FAIL

**Step 3: Commit**

```bash
git add backend/tests/test_tiered_scoring.py
git commit -m "test: add suggested offer price tests #388"
```

---

### Task 3.2: Implement Suggested Offer

**Files:**

- Modify: `backend/app/services/tiered_scoring.py`

**Step 1: Add function**

```python
# Target discount rates by combined score
OFFER_DISCOUNTS = {
    (70, 79): Decimal("0.15"),  # 15% below FMV
    (60, 69): Decimal("0.25"),  # 25% below FMV
    (50, 59): Decimal("0.35"),  # 35% below FMV
    (40, 49): Decimal("0.45"),  # 45% below FMV
    (0, 39): Decimal("0.55"),  # 55% below FMV
}

# Floor-triggered discount rates
STRATEGIC_FLOOR_DISCOUNT = Decimal("0.40")  # 40% below FMV
QUALITY_FLOOR_DISCOUNT = Decimal("0.50")  # 50% below FMV


def calculate_suggested_offer(
    combined_score: int,
    fmv_mid: Decimal | None,
    strategic_floor_applied: bool,
    quality_floor_applied: bool,
) -> Decimal | None:
    """Calculate suggested offer price for CONDITIONAL recommendations.

    Args:
        combined_score: Weighted combined score
        fmv_mid: Midpoint of FMV range
        strategic_floor_applied: True if strategic fit floor was triggered
        quality_floor_applied: True if quality floor was triggered

    Returns:
        Suggested offer price, or None if FMV unknown
    """
    if fmv_mid is None:
        return None

    # Floor-triggered discounts take precedence
    if quality_floor_applied:
        discount = QUALITY_FLOOR_DISCOUNT
    elif strategic_floor_applied:
        discount = STRATEGIC_FLOOR_DISCOUNT
    else:
        # Find discount by combined score
        discount = Decimal("0.55")  # Default to maximum discount
        for (min_score, max_score), disc in OFFER_DISCOUNTS.items():
            if min_score <= combined_score <= max_score:
                discount = disc
                break

    return (fmv_mid * (1 - discount)).quantize(Decimal("1"))
```

**Step 2: Run tests**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestSuggestedOffer -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/app/services/tiered_scoring.py
git commit -m "feat: add suggested offer price calculation #388"
```

---

### Task 3.3: Add Reasoning Generation Tests

**Files:**

- Modify: `backend/tests/test_tiered_scoring.py`

**Step 1: Add tests**

```python
class TestReasoningGeneration:
    """Tests for templated reasoning generation."""

    def test_strong_buy_reasoning(self):
        """STRONG_BUY should include quality driver and discount."""
        from app.services.tiered_scoring import generate_reasoning

        reasoning = generate_reasoning(
            recommendation_tier="STRONG_BUY",
            quality_score=90,
            strategic_fit_score=80,
            price_position="EXCELLENT",
            discount_percent=45,
            publisher_name="Bentley",
            binder_name=None,
            author_name="Wilkie Collins",
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert "STRONG_BUY" not in reasoning  # Tier not repeated in text
        assert "45%" in reasoning or "45" in reasoning
        assert "Bentley" in reasoning or "Collins" in reasoning

    def test_conditional_strategic_floor_reasoning(self):
        """Strategic floor CONDITIONAL should explain wrong publisher."""
        from app.services.tiered_scoring import generate_reasoning

        reasoning = generate_reasoning(
            recommendation_tier="CONDITIONAL",
            quality_score=70,
            strategic_fit_score=15,
            price_position="EXCELLENT",
            discount_percent=60,
            publisher_name="Tauchnitz",
            binder_name=None,
            author_name="Wilkie Collins",
            strategic_floor_applied=True,
            quality_floor_applied=False,
        )
        assert "wrong publisher" in reasoning.lower() or "strategic" in reasoning.lower()

    def test_pass_reasoning(self):
        """PASS should explain primary issue."""
        from app.services.tiered_scoring import generate_reasoning

        reasoning = generate_reasoning(
            recommendation_tier="PASS",
            quality_score=30,
            strategic_fit_score=20,
            price_position="POOR",
            discount_percent=-15,
            publisher_name=None,
            binder_name=None,
            author_name=None,
            strategic_floor_applied=False,
            quality_floor_applied=False,
        )
        assert len(reasoning) > 0
        assert "above FMV" in reasoning.lower() or "overpriced" in reasoning.lower()
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestReasoningGeneration -v`
Expected: FAIL

**Step 3: Commit**

```bash
git add backend/tests/test_tiered_scoring.py
git commit -m "test: add reasoning generation tests #388"
```

---

### Task 3.4: Implement Reasoning Generation

**Files:**

- Modify: `backend/app/services/tiered_scoring.py`

**Step 1: Add function**

```python
def generate_reasoning(
    recommendation_tier: str,
    quality_score: int,
    strategic_fit_score: int,
    price_position: str | None,
    discount_percent: int,
    publisher_name: str | None,
    binder_name: str | None,
    author_name: str | None,
    strategic_floor_applied: bool,
    quality_floor_applied: bool,
    suggested_offer: Decimal | None = None,
) -> str:
    """Generate templated reasoning for recommendation.

    Args:
        recommendation_tier: STRONG_BUY, BUY, CONDITIONAL, or PASS
        quality_score: Quality score (0-100)
        strategic_fit_score: Strategic fit score (0-100)
        price_position: EXCELLENT, GOOD, FAIR, POOR
        discount_percent: Discount from FMV (negative if overpriced)
        publisher_name: Publisher name if available
        binder_name: Binder name if available
        author_name: Author name if available
        strategic_floor_applied: True if strategic floor triggered
        quality_floor_applied: True if quality floor triggered
        suggested_offer: Suggested offer for CONDITIONAL

    Returns:
        1-2 sentence reasoning text
    """
    # Build quality driver description
    quality_drivers = []
    if publisher_name:
        quality_drivers.append(f"Tier 1 publisher ({publisher_name})")
    if binder_name:
        quality_drivers.append(f"premium binding ({binder_name})")

    quality_driver = quality_drivers[0] if quality_drivers else "quality attributes"

    # Generate based on tier
    if recommendation_tier == "STRONG_BUY":
        if discount_percent >= 30:
            return f"Excellent {quality_driver} at {discount_percent}% below FMV. Strong acquisition opportunity."
        else:
            return f"High-quality book with strong strategic fit. {quality_driver} justifies acquisition."

    elif recommendation_tier == "BUY":
        if discount_percent >= 15:
            return f"{quality_driver.capitalize()} at {discount_percent}% below FMV. Good value for collection."
        else:
            return f"Solid strategic fit with acceptable pricing. {quality_driver.capitalize()} adds value."

    elif recommendation_tier == "CONDITIONAL":
        if strategic_floor_applied:
            offer_text = f" Consider at ${suggested_offer} or below." if suggested_offer else ""
            return f"Quality binding/condition but wrong publisher for {author_name or 'author'} collection priority.{offer_text}"
        elif quality_floor_applied:
            offer_text = f" Only acquire at ${suggested_offer} or below." if suggested_offer else ""
            return f"Strategic fit but condition issues limit value.{offer_text}"
        else:
            offer_text = f" Offer ${suggested_offer} for acceptable margin." if suggested_offer else ""
            return f"Asking price at or above FMV.{offer_text}"

    else:  # PASS
        if discount_percent < 0:
            return f"Priced {abs(discount_percent)}% above FMV with limited collection value."
        elif quality_score < 40:
            return "Low quality score with poor strategic fit. Does not meet acquisition criteria."
        else:
            return "Does not meet acquisition criteria at current price point."
```

**Step 2: Run tests**

Run: `poetry run pytest backend/tests/test_tiered_scoring.py::TestReasoningGeneration -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/app/services/tiered_scoring.py
git commit -m "feat: add templated reasoning generation #388"
```

---

## Phase 4: Data Model Migration

### Task 4.1: Create Alembic Migration

**Files:**

- Create: `backend/alembic/versions/xxxx_add_tiered_recommendation_fields.py`

**Step 1: Generate migration**

Run: `cd backend && poetry run alembic revision -m "add tiered recommendation fields"`

**Step 2: Edit migration file**

```python
"""add tiered recommendation fields

Revision ID: [auto-generated]
Revises: [previous]
Create Date: [auto-generated]
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "[auto-generated]"
down_revision = "[previous]"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to eval_runbooks table
    op.add_column(
        "eval_runbooks",
        sa.Column("recommendation_tier", sa.String(20), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("quality_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("strategic_fit_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("combined_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("price_position", sa.String(20), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("suggested_offer", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("recommendation_reasoning", sa.String(500), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("strategic_floor_applied", sa.Boolean(), default=False),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("quality_floor_applied", sa.Boolean(), default=False),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("scoring_version", sa.String(20), default="2025-01"),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("score_source", sa.String(20), default="eval_runbook"),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("last_scored_price", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("napoleon_recommendation", sa.String(20), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("napoleon_reasoning", sa.Text(), nullable=True),
    )
    op.add_column(
        "eval_runbooks",
        sa.Column("napoleon_analyzed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_runbooks", "napoleon_analyzed_at")
    op.drop_column("eval_runbooks", "napoleon_reasoning")
    op.drop_column("eval_runbooks", "napoleon_recommendation")
    op.drop_column("eval_runbooks", "last_scored_price")
    op.drop_column("eval_runbooks", "score_source")
    op.drop_column("eval_runbooks", "scoring_version")
    op.drop_column("eval_runbooks", "quality_floor_applied")
    op.drop_column("eval_runbooks", "strategic_floor_applied")
    op.drop_column("eval_runbooks", "recommendation_reasoning")
    op.drop_column("eval_runbooks", "suggested_offer")
    op.drop_column("eval_runbooks", "price_position")
    op.drop_column("eval_runbooks", "combined_score")
    op.drop_column("eval_runbooks", "strategic_fit_score")
    op.drop_column("eval_runbooks", "quality_score")
    op.drop_column("eval_runbooks", "recommendation_tier")
```

**Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "migration: add tiered recommendation fields to eval_runbooks #388"
```

---

### Task 4.2: Update EvalRunbook Model

**Files:**

- Modify: `backend/app/models/eval_runbook.py`

**Step 1: Add new fields to model**

Add after line 45 (`recommended_price` field):

```python
    # Tiered recommendation fields
    recommendation_tier: Mapped[str | None] = mapped_column(String(20))
    quality_score: Mapped[int | None] = mapped_column(Integer)
    strategic_fit_score: Mapped[int | None] = mapped_column(Integer)
    combined_score: Mapped[int | None] = mapped_column(Integer)
    price_position: Mapped[str | None] = mapped_column(String(20))
    suggested_offer: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    recommendation_reasoning: Mapped[str | None] = mapped_column(String(500))
    strategic_floor_applied: Mapped[bool] = mapped_column(default=False)
    quality_floor_applied: Mapped[bool] = mapped_column(default=False)
    scoring_version: Mapped[str] = mapped_column(String(20), default="2025-01")
    score_source: Mapped[str] = mapped_column(String(20), default="eval_runbook")
    last_scored_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Napoleon Analysis override fields
    napoleon_recommendation: Mapped[str | None] = mapped_column(String(20))
    napoleon_reasoning: Mapped[str | None] = mapped_column(Text)
    napoleon_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime)
```

**Step 2: Run tests to verify model works**

Run: `poetry run pytest backend/tests/test_eval_runbook.py -v`
Expected: All PASS (existing tests still work)

**Step 3: Commit**

```bash
git add backend/app/models/eval_runbook.py
git commit -m "feat: add tiered recommendation fields to EvalRunbook model #388"
```

---

### Task 4.3: Update EvalRunbook Schema

**Files:**

- Modify: `backend/app/schemas/eval_runbook.py`

**Step 1: Add new fields to schemas**

Add to `EvalRunbookBase` after line 41 (`recommended_price`):

```python
    # Tiered recommendation fields
    recommendation_tier: str | None = None
    quality_score: int | None = None
    strategic_fit_score: int | None = None
    combined_score: int | None = None
    price_position: str | None = None
    suggested_offer: Decimal | None = None
    recommendation_reasoning: str | None = None
    strategic_floor_applied: bool = False
    quality_floor_applied: bool = False
    scoring_version: str = "2025-01"
    score_source: str = "eval_runbook"

    # Napoleon Analysis fields
    napoleon_recommendation: str | None = None
    napoleon_reasoning: str | None = None
    napoleon_analyzed_at: datetime | None = None
```

**Step 2: Commit**

```bash
git add backend/app/schemas/eval_runbook.py
git commit -m "feat: add tiered recommendation fields to EvalRunbook schema #388"
```

---

## Phase 5: Integration

### Task 5.1: Update Eval Generation Service

**Files:**

- Modify: `backend/app/services/eval_generation.py`

**Step 1: Import new scoring functions**

Add at top of file:

```python
from app.services.tiered_scoring import (
    calculate_combined_score,
    calculate_price_position,
    calculate_quality_score,
    calculate_strategic_fit_score,
    calculate_suggested_offer,
    determine_recommendation_tier,
    generate_reasoning,
    STRATEGIC_FIT_FLOOR,
    QUALITY_FLOOR,
)
```

**Step 2: Add helper function to check publisher match**

Add after imports:

```python
# Author-publisher requirements (author_name -> required_publisher_name)
AUTHOR_PUBLISHER_REQUIREMENTS = {
    "Wilkie Collins": "Bentley",
    "Charles Dickens": "Chapman",
    # Add more as needed
}


def _check_publisher_matches_author(author_name: str | None, publisher_name: str | None) -> bool:
    """Check if publisher matches the required publisher for this author."""
    if not author_name or not publisher_name:
        return False
    required = AUTHOR_PUBLISHER_REQUIREMENTS.get(author_name)
    if not required:
        return True  # No requirement = matches
    return required.lower() in publisher_name.lower()
```

**Step 3: Update `generate_eval_runbook` function**

After calculating `total_score` (around line 428), add:

```python
    # Calculate tiered recommendation scores
    author_name = book.author.name if book.author else None
    publisher_name = book.publisher.name if book.publisher else None
    binder_name = book.binder.name if book.binder else None

    # Check if publisher matches author requirement
    publisher_matches = _check_publisher_matches_author(author_name, publisher_name)

    # Count author's books in collection
    author_book_count = 0
    if book.author_id:
        from app.models import Book as BookModel
        author_book_count = (
            db.query(BookModel)
            .filter(BookModel.author_id == book.author_id, BookModel.id != book.id)
            .count()
        )

    # Check for duplicates
    is_duplicate = False
    if book.author_id:
        from app.services.scoring import is_duplicate_title
        other_books = (
            db.query(BookModel)
            .filter(BookModel.author_id == book.author_id, BookModel.id != book.id)
            .all()
        )
        for other in other_books:
            if is_duplicate_title(book.title, other.title):
                is_duplicate = True
                break

    # Calculate quality score
    quality_score = calculate_quality_score(
        publisher_tier=book.publisher.tier if book.publisher else None,
        binder_tier=book.binder.tier if book.binder else None,
        year_start=book.year_start,
        condition_grade=condition_grade,
        is_complete=book.is_complete,
        author_priority_score=book.author.priority_score if book.author else 0,
        volume_count=book.volumes or 1,
        is_duplicate=is_duplicate,
    )

    # Calculate strategic fit score
    strategic_fit_score = calculate_strategic_fit_score(
        publisher_matches_author_requirement=publisher_matches,
        author_book_count=author_book_count,
        completes_set=False,  # TODO: Implement set completion detection
    )

    # Calculate combined score and price position
    combined_score = calculate_combined_score(quality_score, strategic_fit_score)
    fmv_mid = None
    if fmv_low and fmv_high:
        fmv_mid = (Decimal(str(fmv_low)) + Decimal(str(fmv_high))) / 2

    price_position = calculate_price_position(
        asking_price=Decimal(str(asking_price)) if asking_price else None,
        fmv_mid=fmv_mid,
    )

    # Check floor conditions
    strategic_floor_applied = strategic_fit_score < STRATEGIC_FIT_FLOOR
    quality_floor_applied = quality_score < QUALITY_FLOOR

    # Determine recommendation tier
    recommendation_tier = determine_recommendation_tier(
        combined_score=combined_score,
        price_position=price_position,
        quality_score=quality_score,
        strategic_fit_score=strategic_fit_score,
    )

    # Calculate suggested offer for CONDITIONAL
    suggested_offer = None
    if recommendation_tier == "CONDITIONAL" and fmv_mid:
        suggested_offer = calculate_suggested_offer(
            combined_score=combined_score,
            fmv_mid=fmv_mid,
            strategic_floor_applied=strategic_floor_applied,
            quality_floor_applied=quality_floor_applied,
        )

    # Calculate discount percent for reasoning
    discount_percent = 0
    if asking_price and fmv_mid:
        discount_percent = int(((float(fmv_mid) - asking_price) / float(fmv_mid)) * 100)

    # Generate reasoning
    recommendation_reasoning = generate_reasoning(
        recommendation_tier=recommendation_tier,
        quality_score=quality_score,
        strategic_fit_score=strategic_fit_score,
        price_position=price_position,
        discount_percent=discount_percent,
        publisher_name=publisher_name,
        binder_name=binder_name,
        author_name=author_name,
        strategic_floor_applied=strategic_floor_applied,
        quality_floor_applied=quality_floor_applied,
        suggested_offer=suggested_offer,
    )

    # Map tier to legacy recommendation for backward compatibility
    legacy_recommendation = "ACQUIRE" if recommendation_tier in ("STRONG_BUY", "BUY") else "PASS"
```

**Step 4: Update runbook creation**

Update the `EvalRunbook(...)` constructor call to include new fields:

```python
    runbook = EvalRunbook(
        book_id=book.id,
        total_score=total_score,
        score_breakdown=score_breakdown,
        recommendation=legacy_recommendation,  # Backward compatible
        recommendation_tier=recommendation_tier,
        quality_score=quality_score,
        strategic_fit_score=strategic_fit_score,
        combined_score=combined_score,
        price_position=price_position,
        suggested_offer=suggested_offer,
        recommendation_reasoning=recommendation_reasoning,
        strategic_floor_applied=strategic_floor_applied,
        quality_floor_applied=quality_floor_applied,
        scoring_version="2025-01",
        score_source="eval_runbook",
        last_scored_price=Decimal(str(asking_price)) if asking_price else None,
        # ... existing fields ...
    )
```

**Step 5: Run tests**

Run: `poetry run pytest backend/tests/test_eval_runbook.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/app/services/eval_generation.py
git commit -m "feat: integrate tiered scoring into eval runbook generation #388"
```

---

## Phase 6: Frontend Updates

### Task 6.1: Update EvalRunbook Store Types

**Files:**

- Modify: `frontend/src/stores/evalRunbook.ts`

**Step 1: Add new fields to EvalRunbook interface**

Find the `EvalRunbook` interface and add:

```typescript
export interface EvalRunbook {
  // ... existing fields ...

  // Tiered recommendation fields
  recommendation_tier?: "STRONG_BUY" | "BUY" | "CONDITIONAL" | "PASS";
  quality_score?: number;
  strategic_fit_score?: number;
  combined_score?: number;
  price_position?: "EXCELLENT" | "GOOD" | "FAIR" | "POOR";
  suggested_offer?: number;
  recommendation_reasoning?: string;
  strategic_floor_applied?: boolean;
  quality_floor_applied?: boolean;
  scoring_version?: string;
  score_source?: "eval_runbook" | "napoleon";

  // Napoleon override fields
  napoleon_recommendation?: string;
  napoleon_reasoning?: string;
  napoleon_analyzed_at?: string;
}
```

**Step 2: Commit**

```bash
git add frontend/src/stores/evalRunbook.ts
git commit -m "feat: add tiered recommendation types to evalRunbook store #388"
```

---

### Task 6.2: Update EvalRunbookModal Display

**Files:**

- Modify: `frontend/src/components/books/EvalRunbookModal.vue`

**Step 1: Add tier badge computed properties**

Add after `scoreBadgeColor` computed:

```typescript
const tierBadgeConfig = computed(() => {
  if (!runbook.value?.recommendation_tier) {
    // Fallback to legacy recommendation
    return runbook.value?.recommendation === "ACQUIRE"
      ? { bg: "bg-green-100", text: "text-green-800", label: "ACQUIRE" }
      : { bg: "bg-yellow-100", text: "text-yellow-800", label: "PASS" };
  }

  const configs: Record<string, { bg: string; text: string; icon: string }> = {
    STRONG_BUY: { bg: "bg-green-500", text: "text-white", icon: "✓✓" },
    BUY: { bg: "bg-green-100", text: "text-green-800", icon: "✓" },
    CONDITIONAL: { bg: "bg-amber-100", text: "text-amber-800", icon: "⚠" },
    PASS: { bg: "bg-gray-100", text: "text-gray-800", icon: "✗" },
  };

  return configs[runbook.value.recommendation_tier] || configs.PASS;
});

const hasNapoleonOverride = computed(() => {
  return (
    runbook.value?.napoleon_recommendation &&
    runbook.value.napoleon_recommendation !== runbook.value.recommendation_tier
  );
});
```

**Step 2: Update Score Summary section template**

Replace the Score Summary section (around line 342-398) with:

```vue
<!-- Score Summary -->
<div class="bg-gray-50 rounded-lg p-4">
  <!-- Tiered Recommendation Badge -->
  <div class="flex items-center justify-between mb-4">
    <div class="flex items-center gap-2">
      <span
        :class="[tierBadgeConfig.bg, tierBadgeConfig.text]"
        class="px-3 py-1.5 rounded-full text-sm font-bold flex items-center gap-1"
      >
        <span v-if="runbook.recommendation_tier">{{ tierBadgeConfig.icon }}</span>
        {{ runbook.recommendation_tier || runbook.recommendation }}
      </span>
      <!-- Napoleon Override Indicator -->
      <span
        v-if="hasNapoleonOverride"
        class="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded"
      >
        Napoleon: {{ runbook.napoleon_recommendation }}
      </span>
    </div>
    <span class="text-sm text-gray-500">
      v{{ runbook.scoring_version || "legacy" }}
    </span>
  </div>

  <!-- Score Bars -->
  <div class="space-y-3">
    <!-- Quality Score -->
    <div v-if="runbook.quality_score !== undefined">
      <div class="flex justify-between text-sm mb-1">
        <span class="text-gray-600">Quality</span>
        <span class="font-medium">{{ runbook.quality_score }}/100</span>
      </div>
      <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          class="h-full bg-blue-500"
          :style="{ width: `${runbook.quality_score}%` }"
        ></div>
      </div>
    </div>

    <!-- Strategic Fit Score -->
    <div v-if="runbook.strategic_fit_score !== undefined">
      <div class="flex justify-between text-sm mb-1">
        <span class="text-gray-600">Strategic Fit</span>
        <span class="font-medium">{{ runbook.strategic_fit_score }}/100</span>
      </div>
      <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          class="h-full"
          :class="runbook.strategic_fit_score < 30 ? 'bg-red-400' : 'bg-green-500'"
          :style="{ width: `${runbook.strategic_fit_score}%` }"
        ></div>
      </div>
      <div v-if="runbook.strategic_floor_applied" class="text-xs text-red-500 mt-1">
        ⚠ Below strategic fit threshold
      </div>
    </div>

    <!-- Price Position -->
    <div v-if="runbook.price_position" class="flex items-center gap-2 text-sm">
      <span class="text-gray-600">Price Position:</span>
      <span
        :class="{
          'text-green-600 font-medium': runbook.price_position === 'EXCELLENT',
          'text-green-500': runbook.price_position === 'GOOD',
          'text-amber-500': runbook.price_position === 'FAIR',
          'text-red-500': runbook.price_position === 'POOR',
        }"
      >
        {{ runbook.price_position }}
      </span>
    </div>
  </div>

  <!-- Reasoning -->
  <div v-if="runbook.recommendation_reasoning" class="mt-4 p-3 bg-white rounded border text-sm text-gray-700">
    {{ runbook.recommendation_reasoning }}
  </div>

  <!-- Suggested Offer (for CONDITIONAL) -->
  <div
    v-if="runbook.recommendation_tier === 'CONDITIONAL' && runbook.suggested_offer"
    class="mt-4 p-3 bg-amber-50 rounded border border-amber-200"
  >
    <div class="text-sm font-medium text-amber-800">Suggested Offer</div>
    <div class="text-lg font-bold text-amber-900">
      {{ formatCurrency(runbook.suggested_offer) }}
    </div>
  </div>

  <!-- Pricing Row -->
  <div class="mt-4 grid grid-cols-4 gap-2 text-sm">
    <!-- ... keep existing pricing row ... -->
  </div>
</div>
```

**Step 3: Commit**

```bash
git add frontend/src/components/books/EvalRunbookModal.vue
git commit -m "feat: update EvalRunbookModal with tiered recommendation display #388"
```

---

## Phase 7: Final Integration Tests

### Task 7.1: Run Full Test Suite

**Step 1: Run all backend tests**

Run: `poetry run pytest backend/tests/ -v`
Expected: All PASS

**Step 2: Run linting**

Run: `poetry run ruff check backend/`
Run: `poetry run ruff format --check backend/`
Expected: No errors

**Step 3: Run frontend checks**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`
Expected: No errors

**Step 4: Commit any fixes**

```bash
git add .
git commit -m "fix: address linting and type issues #388"
```

---

### Task 7.2: Run Migration in Staging

**Step 1: Deploy to staging**

```bash
git push origin staging
```

**Step 2: Run migration**

```bash
curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate
```

**Step 3: Verify API returns new fields**

```bash
bmx-api GET /books/1
```

Expected: Response includes `recommendation_tier`, `quality_score`, `strategic_fit_score`, etc.

---

### Task 7.3: Update GitHub Issue

**Step 1: Comment on issue with completion status**

```bash
gh issue comment 388 --body "## Implementation Complete

All phases implemented:

### Backend
- [x] Quality score calculation (0-100)
- [x] Strategic fit score calculation (0-100)
- [x] Recommendation matrix with STRONG_BUY/BUY/CONDITIONAL/PASS
- [x] Floor rules (strategic fit < 30, quality < 40 → cap at CONDITIONAL)
- [x] Suggested offer price for CONDITIONAL
- [x] Templated reasoning generation
- [x] Data model migration
- [x] Integration with eval_generation.py

### Frontend
- [x] Updated EvalRunbookModal with tier badges
- [x] Quality/Strategic Fit score bars
- [x] Reasoning display
- [x] Suggested offer for CONDITIONAL
- [x] Napoleon override indicator

### Tests
- [x] All scoring function tests passing
- [x] Integration tests passing

Ready for review and merge to main."
```

---

## Success Criteria Checklist

- [ ] Quality score calculated correctly (0-100)
- [ ] Strategic fit score calculated correctly (0-100)
- [ ] Combined score uses 60/40 weighting
- [ ] Recommendation matrix produces correct tiers
- [ ] Strategic fit floor (< 30) caps at CONDITIONAL
- [ ] Quality floor (< 40) caps at CONDITIONAL
- [ ] CONDITIONAL includes suggested offer price
- [ ] All recommendations include reasoning text
- [ ] Napoleon Analysis can override (field exists)
- [ ] Price changes tracked via `last_scored_price`
- [ ] Frontend displays tiered badges correctly
- [ ] Backward compatible with legacy `recommendation` field
- [ ] All tests passing
- [ ] Linting passing
