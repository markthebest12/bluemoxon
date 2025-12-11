"""Scoring engine for book acquisition evaluation."""

import re
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
