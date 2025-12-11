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
