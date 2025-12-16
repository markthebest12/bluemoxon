"""Eval Runbook generation service.

This service generates the lightweight evaluation report based on:
1. Book metadata from eBay listing
2. Images analysis via Claude
3. FMV lookup from eBay sold + AbeBooks

TODO: Implement FMV lookup integration
TODO: Implement Claude evaluation prompt
"""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Book, EvalRunbook

logger = logging.getLogger(__name__)

ACQUIRE_THRESHOLD = 80


def generate_eval_runbook(
    book: Book,
    listing_data: dict,
    db: Session,
) -> EvalRunbook:
    """Generate eval runbook for a book.

    Args:
        book: Book model instance
        listing_data: Raw data from eBay listing import
        db: Database session

    Returns:
        Created EvalRunbook instance

    Note: This is a placeholder. Full implementation will include:
    - FMV lookup from eBay/AbeBooks
    - Claude-based condition assessment
    - Strategic scoring calculation
    """
    logger.info(f"Generating eval runbook for book {book.id}: {book.title}")

    # Placeholder scoring - will be replaced with actual logic
    score_breakdown = {
        "Tier 1 Publisher": {"points": 0, "notes": "TBD"},
        "Victorian Era": {"points": 0, "notes": "TBD"},
        "Complete Set": {"points": 0, "notes": "TBD"},
        "Condition": {"points": 0, "notes": "TBD"},
        "Premium Binding": {"points": 0, "notes": "TBD"},
        "Price vs FMV": {"points": 0, "notes": "TBD"},
    }

    total_score = sum(item["points"] for item in score_breakdown.values())
    recommendation = "ACQUIRE" if total_score >= ACQUIRE_THRESHOLD else "PASS"

    asking_price = listing_data.get("price")

    runbook = EvalRunbook(
        book_id=book.id,
        total_score=total_score,
        score_breakdown=score_breakdown,
        recommendation=recommendation,
        original_asking_price=Decimal(str(asking_price)) if asking_price else None,
        current_asking_price=Decimal(str(asking_price)) if asking_price else None,
        item_identification={
            "Title": book.title,
            "Author": listing_data.get("author", "Unknown"),
            "Publisher": listing_data.get("publisher", "Unknown"),
        },
        analysis_narrative="Evaluation pending. Full analysis will be generated after FMV lookup.",
    )

    db.add(runbook)
    db.commit()
    db.refresh(runbook)

    logger.info(f"Created eval runbook {runbook.id} for book {book.id}, score={total_score}")

    return runbook
