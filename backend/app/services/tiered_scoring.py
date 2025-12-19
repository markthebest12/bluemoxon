"""Tiered recommendation scoring engine.

This module calculates Quality Score and Strategic Fit Score for the
tiered recommendation system (STRONG_BUY/BUY/CONDITIONAL/PASS).

See docs/plans/2025-12-19-tiered-recommendations-design.md for full design.
"""

from __future__ import annotations

from decimal import Decimal

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
