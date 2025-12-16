"""Eval Runbook generation service.

This service generates the lightweight evaluation report based on:
1. Book metadata from eBay listing
2. Book's existing attributes (publisher tier, binder, condition, etc.)
3. FMV comparison when value estimates are available

TODO: Implement FMV lookup from eBay/AbeBooks comparables
TODO: Implement Claude-based condition assessment from images
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Book, EvalRunbook

logger = logging.getLogger(__name__)

ACQUIRE_THRESHOLD = 80

# Victorian era: 1837 (Victoria's accession) to 1901 (her death)
VICTORIAN_START = 1837
VICTORIAN_END = 1901

# Tier 1 binders (premium binding attribution)
TIER_1_BINDERS = {"Rivière & Son", "Riviere", "Zaehnsdorf", "Sangorski & Sutcliffe", "Sangorski", "Cobden-Sanderson", "Bedford"}


def _calculate_publisher_score(book: Book) -> tuple[int, str]:
    """Calculate Tier 1 Publisher score (max 20 points)."""
    if book.publisher and hasattr(book.publisher, "tier") and book.publisher.tier == "TIER_1":
        return 20, f"✓ {book.publisher.name} (Tier 1)"
    elif book.publisher:
        return 0, f"{book.publisher.name} - NOT Tier 1"
    return 0, "No publisher identified"


def _calculate_victorian_score(book: Book) -> tuple[int, str]:
    """Calculate Victorian Era score (max 30 points)."""
    if book.year_start:
        if VICTORIAN_START <= book.year_start <= VICTORIAN_END:
            return 30, f"✓ {book.year_start}"
        else:
            return 0, f"{book.year_start} - outside Victorian era"
    return 0, "Publication year unknown"


def _calculate_complete_set_score(book: Book) -> tuple[int, str]:
    """Calculate Complete Set score (max 20 points)."""
    if book.is_complete:
        if book.volumes == 1:
            return 20, "✓ Single volume"
        else:
            return 20, f"✓ Complete set ({book.volumes} volumes)"
    else:
        return 0, f"Incomplete - missing volumes from {book.volumes}-volume set"


def _calculate_condition_score(book: Book) -> tuple[int, str]:
    """Calculate Condition score (max 15 points)."""
    condition = book.condition_grade or ""
    condition_lower = condition.lower()

    # Score based on condition grade
    if "fine" in condition_lower or "mint" in condition_lower:
        points = 15
        notes = f"✓ {condition}"
    elif "very good" in condition_lower or "vg+" in condition_lower:
        points = 12
        notes = f"✓ {condition}"
    elif "good" in condition_lower:
        points = 10
        notes = f"{condition}"
    elif "fair" in condition_lower:
        points = 5
        notes = f"{condition} (condition penalty)"
    elif "poor" in condition_lower:
        points = 0
        notes = f"{condition} (significant condition issues)"
    else:
        points = 8  # Unknown condition, assume average
        notes = "Condition not assessed"

    # Check for foxing in condition_notes
    if book.condition_notes and "foxing" in book.condition_notes.lower():
        if "heavy" in book.condition_notes.lower() or "significant" in book.condition_notes.lower():
            points = max(0, points - 5)
            notes += " (foxing penalty)"
        else:
            points = max(0, points - 2)
            notes += " (minor foxing)"

    return points, notes


def _calculate_binding_score(book: Book) -> tuple[int, str]:
    """Calculate Premium Binding score (max 15 points)."""
    if book.binder:
        binder_name = book.binder.name
        # Check if Tier 1 binder
        if any(tier1 in binder_name for tier1 in TIER_1_BINDERS):
            return 15, f"✓ {binder_name} (premium binder)"
        elif hasattr(book.binder, "tier") and book.binder.tier == "TIER_2":
            return 10, f"{binder_name} (Tier 2 binder)"
        else:
            return 5, f"{binder_name}"
    elif book.binding_type:
        binding_lower = book.binding_type.lower()
        if "morocco" in binding_lower or "leather" in binding_lower:
            return 5, f"{book.binding_type} (no binder signature)"
        return 0, f"{book.binding_type}"
    return 0, "No binder signature"


def _calculate_price_score(book: Book, asking_price: float | None) -> tuple[int, str]:
    """Calculate Price vs FMV score (max 20 points)."""
    if not asking_price:
        return 0, "No asking price"

    # Use book's value estimates if available
    fmv_low = float(book.value_low) if book.value_low else None
    fmv_high = float(book.value_high) if book.value_high else None

    if fmv_low and fmv_high:
        fmv_mid = (fmv_low + fmv_high) / 2
        discount_pct = ((fmv_mid - asking_price) / fmv_mid) * 100

        if discount_pct >= 30:
            return 20, f"{discount_pct:.0f}% below FMV (excellent)"
        elif discount_pct >= 15:
            return 10, f"{discount_pct:.0f}% below FMV (good)"
        elif discount_pct >= 0:
            return 5, "At or near FMV"
        else:
            return 0, f"{abs(discount_pct):.0f}% above FMV"

    return 0, "FMV not yet determined"


def generate_eval_runbook(
    book: Book,
    listing_data: dict,
    db: Session,
) -> EvalRunbook:
    """Generate eval runbook for a book.

    Args:
        book: Book model instance with relationships loaded
        listing_data: Data from listing import containing:
            - price: Asking price
            - author: Author name
            - publisher: Publisher name
        db: Database session

    Returns:
        Created EvalRunbook instance
    """
    logger.info(f"Generating eval runbook for book {book.id}: {book.title}")

    asking_price = listing_data.get("price")

    # Calculate each scoring criterion
    publisher_points, publisher_notes = _calculate_publisher_score(book)
    victorian_points, victorian_notes = _calculate_victorian_score(book)
    complete_points, complete_notes = _calculate_complete_set_score(book)
    condition_points, condition_notes = _calculate_condition_score(book)
    binding_points, binding_notes = _calculate_binding_score(book)
    price_points, price_notes = _calculate_price_score(book, asking_price)

    score_breakdown = {
        "Tier 1 Publisher": {"points": publisher_points, "notes": publisher_notes},
        "Victorian Era": {"points": victorian_points, "notes": victorian_notes},
        "Complete Set": {"points": complete_points, "notes": complete_notes},
        "Condition": {"points": condition_points, "notes": condition_notes},
        "Premium Binding": {"points": binding_points, "notes": binding_notes},
        "Price vs FMV": {"points": price_points, "notes": price_notes},
    }

    total_score = sum(item["points"] for item in score_breakdown.values())
    recommendation = "ACQUIRE" if total_score >= ACQUIRE_THRESHOLD else "PASS"

    # Build analysis narrative
    narrative_parts = []
    if total_score >= ACQUIRE_THRESHOLD:
        narrative_parts.append(f"This book scores {total_score}/120, meeting the {ACQUIRE_THRESHOLD}-point acquisition threshold.")
    else:
        points_needed = ACQUIRE_THRESHOLD - total_score
        narrative_parts.append(f"This book scores {total_score}/120, {points_needed} points below the acquisition threshold.")

    # Add key observations
    if binding_points >= 15:
        narrative_parts.append(f"The {book.binder.name if book.binder else 'premium'} binding adds significant collector value.")
    if victorian_points == 0 and book.year_start:
        narrative_parts.append(f"Published in {book.year_start}, outside the Victorian era target range.")
    if price_points == 0 and asking_price:
        narrative_parts.append("Current asking price is at or above fair market value.")

    analysis_narrative = " ".join(narrative_parts)

    # Get FMV values from book if available
    fmv_low = book.value_low
    fmv_high = book.value_high

    runbook = EvalRunbook(
        book_id=book.id,
        total_score=total_score,
        score_breakdown=score_breakdown,
        recommendation=recommendation,
        original_asking_price=Decimal(str(asking_price)) if asking_price else None,
        current_asking_price=Decimal(str(asking_price)) if asking_price else None,
        fmv_low=fmv_low,
        fmv_high=fmv_high,
        condition_grade=book.condition_grade,
        item_identification={
            "Title": book.title,
            "Author": listing_data.get("author", "Unknown"),
            "Publisher": listing_data.get("publisher", "Unknown"),
            "Year": str(book.year_start) if book.year_start else "Unknown",
            "Binder": book.binder.name if book.binder else None,
        },
        analysis_narrative=analysis_narrative,
        generated_at=datetime.utcnow(),
    )

    db.add(runbook)
    db.commit()
    db.refresh(runbook)

    logger.info(f"Created eval runbook {runbook.id} for book {book.id}, score={total_score}, recommendation={recommendation}")

    return runbook
