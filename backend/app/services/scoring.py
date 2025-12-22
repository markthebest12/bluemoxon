"""Scoring engine for book acquisition evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.services.set_detection import detect_set_completion

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Book


@dataclass
class ScoreFactor:
    """A single scoring factor with explanation."""

    name: str
    points: int
    reason: str


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a score component."""

    score: int
    factors: list[ScoreFactor] = field(default_factory=list)

    def add(self, name: str, points: int, reason: str) -> None:
        """Add a factor to the breakdown."""
        self.factors.append(ScoreFactor(name, points, reason))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": self.score,
            "factors": [
                {"name": f.name, "points": f.points, "reason": f.reason} for f in self.factors
            ],
        }


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
    - 0-19%: 5
    - Overpriced (negative discount): 0
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
    elif discount_pct >= 0:
        return 5
    else:
        # Overpriced - negative discount (paying more than market value)
        return 0


def author_tier_to_score(tier: str | None) -> int:
    """Convert author tier to priority score.

    TIER_1: +15 (Darwin, Lyell - Victorian Science)
    TIER_2: +10 (Dickens, Collins - Victorian Novelists)
    TIER_3: +5 (Ruskin - Art Criticism)
    """
    if tier == "TIER_1":
        return 15
    elif tier == "TIER_2":
        return 10
    elif tier == "TIER_3":
        return 5
    return 0


def calculate_strategic_fit(
    publisher_tier: str | None,
    binder_tier: str | None,
    year_start: int | None,
    is_complete: bool,
    condition_grade: str | None,
    author_priority_score: int,
    volume_count: int = 1,
) -> int:
    """
    Calculate strategic fit score based on collection criteria.

    Factors:
    - Tier 1 Publisher: +35
    - Tier 2 Publisher: +15
    - Tier 1 Binder: +40
    - Tier 2 Binder: +20
    - DOUBLE TIER 1 Bonus: +15 (both publisher AND binder are Tier 1)
    - Victorian/Romantic Era: +20
    - Complete Set: +15
    - Good+ Condition: +15
    - Author Priority: variable (0-50)
    - Volume Penalty: -10 (4 vols), -20 (5+ vols)

    Returns score 0-100+ (can exceed 100 with high author priority).
    """
    score = 0

    # Publisher tier
    if publisher_tier == "TIER_1":
        score += 35
    elif publisher_tier == "TIER_2":
        score += 15

    # Binder tier
    if binder_tier == "TIER_1":
        score += 40
    elif binder_tier == "TIER_2":
        score += 20

    # DOUBLE TIER 1 bonus - when both publisher AND binder are Tier 1
    if publisher_tier == "TIER_1" and binder_tier == "TIER_1":
        score += 15

    # Era (Victorian 1837-1901, Romantic 1800-1836)
    if year_start is not None:
        if 1800 <= year_start <= 1901:
            score += 20

    # Complete set
    if is_complete:
        score += 15

    # Condition (Good or better) - expanded to include VG variants
    if condition_grade in ("Fine", "VG+", "VG", "Very Good", "VG-", "Good+", "Good"):
        score += 15

    # Volume penalty - graduated scale
    if volume_count == 4:
        score -= 10
    elif volume_count >= 5:
        score -= 20

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


def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles using token-based Jaccard similarity.

    Args:
        title1: First title
        title2: Second title

    Returns:
        Similarity score between 0 and 1
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    # Exact match after normalization
    if norm1 == norm2:
        return 1.0

    # Token-based similarity (Jaccard)
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union


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
    return calculate_title_similarity(title1, title2) >= threshold


def calculate_collection_impact(
    author_book_count: int,
    is_duplicate: bool,
    completes_set: bool,
    volume_count: int,  # Kept for API compatibility, but penalty moved to strategic_fit
) -> int:
    """
    Calculate collection impact score.

    Factors:
    - New author (0 existing): +30
    - Fills author gap (1 existing): +15
    - Duplicate title: -40
    - Completes incomplete set: +25

    Note: Volume penalty moved to strategic_fit for graduated scale.

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

    return score


def calculate_all_scores(
    purchase_price: Decimal | None,
    value_mid: Decimal | None,
    publisher_tier: str | None,
    binder_tier: str | None,
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
        publisher_tier,
        binder_tier,
        year_start,
        is_complete,
        condition_grade,
        author_priority_score,
        volume_count,
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


def calculate_investment_grade_breakdown(
    purchase_price: Decimal | None,
    value_mid: Decimal | None,
) -> ScoreBreakdown:
    """Calculate investment grade with detailed breakdown."""
    if purchase_price is None or value_mid is None:
        breakdown = ScoreBreakdown(score=0)
        breakdown.add("missing_data", 0, "Missing purchase price or market value")
        return breakdown

    if value_mid <= 0:
        breakdown = ScoreBreakdown(score=0)
        breakdown.add("invalid_value", 0, "Market value must be positive")
        return breakdown

    discount_pct = float((value_mid - purchase_price) / value_mid * 100)
    score = calculate_investment_grade(purchase_price, value_mid)

    breakdown = ScoreBreakdown(score=score)
    breakdown.add(
        "discount",
        score,
        f"{discount_pct:.1f}% discount (${float(purchase_price):.0f} vs ${float(value_mid):.0f} market value)",
    )
    return breakdown


def calculate_strategic_fit_breakdown(
    publisher_tier: str | None,
    binder_tier: str | None,
    year_start: int | None,
    is_complete: bool,
    condition_grade: str | None,
    author_priority_score: int,
    volume_count: int = 1,
    author_name: str | None = None,
    publisher_name: str | None = None,
    binder_name: str | None = None,
    author_tier: str | None = None,
) -> ScoreBreakdown:
    """Calculate strategic fit with detailed breakdown."""
    score = 0
    breakdown = ScoreBreakdown(score=0)  # Will update at end

    # Publisher tier
    if publisher_tier == "TIER_1":
        score += 35
        breakdown.add(
            "publisher_tier",
            35,
            f"Tier 1 publisher{f' ({publisher_name})' if publisher_name else ''}",
        )
    elif publisher_tier == "TIER_2":
        score += 15
        breakdown.add(
            "publisher_tier",
            15,
            f"Tier 2 publisher{f' ({publisher_name})' if publisher_name else ''}",
        )
    elif publisher_tier:
        breakdown.add(
            "publisher_tier",
            0,
            f"Non-premium publisher tier ({publisher_tier})",
        )
    else:
        breakdown.add("publisher_tier", 0, "Publisher tier not specified")

    # Binder tier
    if binder_tier == "TIER_1":
        score += 40
        breakdown.add(
            "binder_tier",
            40,
            f"Tier 1 binder{f' ({binder_name})' if binder_name else ''}",
        )
    elif binder_tier == "TIER_2":
        score += 20
        breakdown.add(
            "binder_tier",
            20,
            f"Tier 2 binder{f' ({binder_name})' if binder_name else ''}",
        )
    elif binder_tier:
        breakdown.add(
            "binder_tier",
            0,
            f"Non-premium binder tier ({binder_tier})",
        )
    # No "not specified" message for binder - many books don't have authenticated binders

    # DOUBLE TIER 1 bonus
    if publisher_tier == "TIER_1" and binder_tier == "TIER_1":
        score += 15
        breakdown.add(
            "double_tier_1",
            15,
            "DOUBLE TIER 1 bonus (both publisher and binder are Tier 1)",
        )

    # Era
    if year_start is not None:
        if 1800 <= year_start <= 1901:
            score += 20
            if 1837 <= year_start <= 1901:
                breakdown.add("era", 20, f"Victorian era ({year_start})")
            else:
                breakdown.add("era", 20, f"Romantic era ({year_start})")
        else:
            breakdown.add("era", 0, f"Outside target period ({year_start})")
    else:
        breakdown.add("era", 0, "Publication year not specified")

    # Complete set
    if is_complete:
        score += 15
        breakdown.add("completeness", 15, "Complete set")
    else:
        breakdown.add("completeness", 0, "Incomplete or multi-volume set")

    # Condition - expanded to include VG variants
    if condition_grade in ("Fine", "VG+", "VG", "Very Good", "VG-", "Good+", "Good"):
        score += 15
        breakdown.add("condition", 15, f"{condition_grade} condition")
    elif condition_grade:
        breakdown.add("condition", 0, f"{condition_grade} condition (below Good)")
    else:
        breakdown.add("condition", 0, "Condition not specified")

    # Volume penalty - graduated scale
    if volume_count == 4:
        score -= 10
        breakdown.add("volume_penalty", -10, "4-volume set storage consideration")
    elif volume_count >= 5:
        score -= 20
        breakdown.add("volume_penalty", -20, f"Large set ({volume_count} volumes)")
    elif volume_count > 1:
        breakdown.add("volume_count", 0, f"Multi-volume ({volume_count} volumes)")

    # Author priority
    if author_priority_score > 0:
        score += author_priority_score
        tier_label = {"TIER_1": "Tier 1", "TIER_2": "Tier 2", "TIER_3": "Tier 3"}.get(
            author_tier, "Priority"
        )
        breakdown.add(
            "author_priority",
            author_priority_score,
            f"{author_name} - {tier_label} author (+{author_priority_score})",
        )
    elif author_name:
        breakdown.add("author_priority", 0, f"{author_name} - not a priority author")

    breakdown.score = score
    return breakdown


def calculate_collection_impact_breakdown(
    author_book_count: int,
    is_duplicate: bool,
    completes_set: bool,
    volume_count: int,  # Kept for API compatibility, but penalty moved to strategic_fit
    author_name: str | None = None,
    duplicate_title: str | None = None,
) -> ScoreBreakdown:
    """Calculate collection impact with detailed breakdown.

    Note: Volume penalty moved to strategic_fit_breakdown for graduated scale.
    """
    score = 0
    breakdown = ScoreBreakdown(score=0)  # Will update at end

    # Author presence
    if author_book_count == 0:
        score += 30
        breakdown.add(
            "author_presence",
            30,
            f"New author to collection{f' ({author_name})' if author_name else ''}",
        )
    elif author_book_count == 1:
        score += 15
        breakdown.add(
            "author_presence",
            15,
            f"Second work by author{f' ({author_name})' if author_name else ''} - builds depth",
        )
    else:
        breakdown.add(
            "author_presence",
            0,
            f"Already have {author_book_count} works by {author_name or 'this author'}",
        )

    # Duplicate check
    if is_duplicate:
        score -= 40
        reason = "Duplicate title in collection"
        if duplicate_title:
            reason = f"Duplicate of existing title: {duplicate_title}"
        breakdown.add("duplicate", -40, reason)
    else:
        breakdown.add("duplicate", 0, "No duplicate title found in collection")

    # Set completion
    if completes_set:
        score += 25
        breakdown.add("set_completion", 25, "Completes an incomplete set")

    breakdown.score = score
    return breakdown


def calculate_all_scores_with_breakdown(
    purchase_price: Decimal | None,
    value_mid: Decimal | None,
    publisher_tier: str | None,
    binder_tier: str | None,
    year_start: int | None,
    is_complete: bool,
    condition_grade: str | None,
    author_priority_score: int,
    author_book_count: int,
    is_duplicate: bool,
    completes_set: bool,
    volume_count: int,
    author_name: str | None = None,
    publisher_name: str | None = None,
    binder_name: str | None = None,
    duplicate_title: str | None = None,
    author_tier: str | None = None,
) -> dict:
    """
    Calculate all scores with detailed breakdowns.

    Returns:
        Dict with scores and detailed factor breakdowns for each component.
    """
    investment = calculate_investment_grade_breakdown(purchase_price, value_mid)
    strategic = calculate_strategic_fit_breakdown(
        publisher_tier,
        binder_tier,
        year_start,
        is_complete,
        condition_grade,
        author_priority_score,
        volume_count,
        author_name,
        publisher_name,
        binder_name,
        author_tier,
    )
    collection = calculate_collection_impact_breakdown(
        author_book_count,
        is_duplicate,
        completes_set,
        volume_count,
        author_name,
        duplicate_title,
    )

    overall = investment.score + strategic.score + collection.score

    return {
        "investment_grade": investment.score,
        "strategic_fit": strategic.score,
        "collection_impact": collection.score,
        "overall_score": overall,
        "breakdown": {
            "investment_grade": investment.to_dict(),
            "strategic_fit": strategic.to_dict(),
            "collection_impact": collection.to_dict(),
        },
    }


def calculate_and_persist_book_scores(book: Book, db: Session) -> dict[str, int]:
    """
    Calculate and persist scores for a book.

    This is a shared helper that can be called from API endpoints or background workers.

    Args:
        book: The book model to score (must have relationships loaded)
        db: Database session

    Returns:
        Dict with investment_grade, strategic_fit, collection_impact, overall_score
    """
    # Import here to avoid circular imports
    from app.models import Book as BookModel

    author_priority = 0
    author_tier = None
    publisher_tier = None
    binder_tier = None
    author_book_count = 0

    if book.author:
        author_tier = book.author.tier
        author_priority = author_tier_to_score(author_tier)
        author_book_count = (
            db.query(BookModel)
            .filter(BookModel.author_id == book.author_id, BookModel.id != book.id)
            .count()
        )

    if book.publisher:
        publisher_tier = book.publisher.tier

    if book.binder:
        binder_tier = book.binder.tier

    is_duplicate = False
    if book.author_id:
        other_books = (
            db.query(BookModel)
            .filter(BookModel.author_id == book.author_id, BookModel.id != book.id)
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
        binder_tier=binder_tier,
        year_start=book.year_start,
        is_complete=book.is_complete,
        condition_grade=book.condition_grade,
        author_priority_score=author_priority,
        author_book_count=author_book_count,
        is_duplicate=is_duplicate,
        completes_set=detect_set_completion(
            db=db,
            author_id=book.author_id,
            title=book.title,
            volumes=book.volumes or 1,
            book_id=book.id,
        ),
        volume_count=book.volumes or 1,
    )

    book.investment_grade = scores["investment_grade"]
    book.strategic_fit = scores["strategic_fit"]
    book.collection_impact = scores["collection_impact"]
    book.overall_score = scores["overall_score"]
    book.scores_calculated_at = datetime.now()

    return scores
