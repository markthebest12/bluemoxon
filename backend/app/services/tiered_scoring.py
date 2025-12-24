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
QUALITY_LARGE_VOLUME_PENALTY = 0  # Issue #587: removed penalty, large sets noted only

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


# Floor thresholds for recommendations
STRATEGIC_FIT_FLOOR = 30
QUALITY_FLOOR = 40

# Recommendation tier constants
STRONG_BUY = "STRONG_BUY"
BUY = "BUY"
CONDITIONAL = "CONDITIONAL"
PASS = "PASS"


def determine_recommendation_tier(
    combined_score: int,
    price_position: str | None,
    quality_score: int,
    strategic_fit_score: int,
) -> str:
    """Determine recommendation tier based on scores and price position.

    Uses a matrix approach with floor rules to prevent "great deal, wrong book"
    recommendations.

    Floor rules (cap at CONDITIONAL regardless of matrix):
    - Strategic Fit < 30: Wrong book for collection strategy
    - Quality < 40: Book doesn't meet quality standards

    Matrix (combined score × price position):
    | Combined Score | EXCELLENT   | GOOD        | FAIR        | POOR        |
    |----------------|-------------|-------------|-------------|-------------|
    | ≥ 80           | STRONG_BUY  | STRONG_BUY  | BUY         | CONDITIONAL |
    | 60-79          | STRONG_BUY  | BUY         | CONDITIONAL | PASS        |
    | 40-59          | BUY         | CONDITIONAL | PASS        | PASS        |
    | < 40           | CONDITIONAL | PASS        | PASS        | PASS        |

    Args:
        combined_score: Combined score (0-100)
        price_position: EXCELLENT, GOOD, FAIR, POOR, or None
        quality_score: Quality score (0-100) for floor check
        strategic_fit_score: Strategic fit score (0-100) for floor check

    Returns:
        STRONG_BUY, BUY, CONDITIONAL, or PASS
    """
    # Apply floor rules - check if we need to cap at CONDITIONAL
    floor_triggered = strategic_fit_score < STRATEGIC_FIT_FLOOR or quality_score < QUALITY_FLOOR

    # Treat missing price position as FAIR
    effective_price = price_position if price_position else "FAIR"

    # Recommendation matrix lookup
    if combined_score >= 80:
        matrix_row = {
            "EXCELLENT": STRONG_BUY,
            "GOOD": STRONG_BUY,
            "FAIR": BUY,
            "POOR": CONDITIONAL,
        }
    elif combined_score >= 60:
        matrix_row = {
            "EXCELLENT": STRONG_BUY,
            "GOOD": BUY,
            "FAIR": CONDITIONAL,
            "POOR": PASS,
        }
    elif combined_score >= 40:
        matrix_row = {
            "EXCELLENT": BUY,
            "GOOD": CONDITIONAL,
            "FAIR": PASS,
            "POOR": PASS,
        }
    else:
        matrix_row = {
            "EXCELLENT": CONDITIONAL,
            "GOOD": PASS,
            "FAIR": PASS,
            "POOR": PASS,
        }

    tier = matrix_row.get(effective_price, PASS)

    # Apply floor cap - downgrade to CONDITIONAL if floor triggered
    # but only if the matrix gave us something better than CONDITIONAL
    if floor_triggered and tier in (STRONG_BUY, BUY):
        return CONDITIONAL

    return tier


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
    if recommendation_tier == STRONG_BUY:
        if discount_percent >= 30:
            return f"Excellent {quality_driver} at {discount_percent}% below FMV. Strong acquisition opportunity."
        else:
            return f"High-quality book with strong strategic fit. {quality_driver} justifies acquisition."

    elif recommendation_tier == BUY:
        if discount_percent >= 15:
            return f"{quality_driver.capitalize()} at {discount_percent}% below FMV. Good value for collection."
        else:
            return f"Solid strategic fit with acceptable pricing. {quality_driver.capitalize()} adds value."

    elif recommendation_tier == CONDITIONAL:
        if strategic_floor_applied:
            offer_text = f" Consider at ${suggested_offer} or below." if suggested_offer else ""
            return f"Quality binding/condition but wrong publisher for {author_name or 'author'} collection priority.{offer_text}"
        elif quality_floor_applied:
            offer_text = f" Only acquire at ${suggested_offer} or below." if suggested_offer else ""
            return f"Strategic fit but condition issues limit value.{offer_text}"
        else:
            offer_text = (
                f" Offer ${suggested_offer} for acceptable margin." if suggested_offer else ""
            )
            return f"Asking price at or above FMV.{offer_text}"

    else:  # PASS
        if discount_percent < 0:
            return f"Priced {abs(discount_percent)}% above FMV with limited collection value."
        elif quality_score < 40:
            return "Low quality score with poor strategic fit. Does not meet acquisition criteria."
        else:
            return "Does not meet acquisition criteria at current price point."
