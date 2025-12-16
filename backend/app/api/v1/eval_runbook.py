"""Eval Runbook API endpoints."""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.db import get_db
from app.models import Book, EvalPriceHistory, EvalRunbook, User
from app.schemas.eval_runbook import (
    EvalPriceHistoryResponse,
    EvalRunbookPriceUpdate,
    EvalRunbookPriceUpdateResponse,
    EvalRunbookResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

ACQUIRE_THRESHOLD = 80


def calculate_recommendation(score: int) -> str:
    """Determine recommendation based on score threshold."""
    return "ACQUIRE" if score >= ACQUIRE_THRESHOLD else "PASS"


def recalculate_score_for_price(
    runbook: EvalRunbook,
    new_price: Decimal,
) -> tuple[int, dict]:
    """Recalculate score when price changes.

    Returns (new_total_score, updated_breakdown).
    Only the 'Price vs FMV' criterion changes.
    """
    breakdown = dict(runbook.score_breakdown)
    fmv_mid = (
        (runbook.fmv_low + runbook.fmv_high) / 2 if runbook.fmv_low and runbook.fmv_high else None
    )

    # Calculate price points
    price_points = 0
    price_notes = "No FMV data"

    if fmv_mid and new_price:
        discount_pct = ((fmv_mid - new_price) / fmv_mid) * 100
        if discount_pct >= 30:
            price_points = 20
            price_notes = f"{discount_pct:.0f}% below FMV (excellent)"
        elif discount_pct >= 15:
            price_points = 10
            price_notes = f"{discount_pct:.0f}% below FMV (good)"
        elif discount_pct >= 0:
            price_points = 5
            price_notes = "At or near FMV"
        else:
            price_points = 0
            price_notes = f"{abs(discount_pct):.0f}% above FMV"

    # Update breakdown
    breakdown["Price vs FMV"] = {"points": price_points, "notes": price_notes}

    # Recalculate total
    new_total = sum(item["points"] for item in breakdown.values())

    return new_total, breakdown


@router.get("", response_model=EvalRunbookResponse)
def get_eval_runbook(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Get eval runbook for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    runbook = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).first()
    if not runbook:
        raise HTTPException(status_code=404, detail="Eval runbook not found")

    return runbook


@router.patch("/price", response_model=EvalRunbookPriceUpdateResponse)
def update_eval_runbook_price(
    book_id: int,
    price_update: EvalRunbookPriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Update asking price and recalculate score."""
    runbook = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).first()
    if not runbook:
        raise HTTPException(status_code=404, detail="Eval runbook not found")

    # Store old values
    previous_price = runbook.current_asking_price
    score_before = runbook.total_score
    recommendation_before = runbook.recommendation

    # Recalculate score
    new_score, new_breakdown = recalculate_score_for_price(runbook, price_update.new_price)
    new_recommendation = calculate_recommendation(new_score)

    # Create price history record
    history = EvalPriceHistory(
        eval_runbook_id=runbook.id,
        previous_price=previous_price,
        new_price=price_update.new_price,
        discount_code=price_update.discount_code,
        notes=price_update.notes,
        score_before=score_before,
        score_after=new_score,
        changed_at=datetime.utcnow(),
    )
    db.add(history)

    # Update runbook
    runbook.current_asking_price = price_update.new_price
    runbook.discount_code = price_update.discount_code
    runbook.price_notes = price_update.notes
    runbook.total_score = new_score
    runbook.score_breakdown = new_breakdown
    runbook.recommendation = new_recommendation
    runbook.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(runbook)

    logger.info(
        f"Updated eval runbook price for book {book_id}: ${previous_price} -> ${price_update.new_price}, score {score_before} -> {new_score}"
    )

    return EvalRunbookPriceUpdateResponse(
        previous_price=previous_price,
        new_price=price_update.new_price,
        score_before=score_before,
        score_after=new_score,
        recommendation_before=recommendation_before,
        recommendation_after=new_recommendation,
        runbook=runbook,
    )


@router.get("/history", response_model=list[EvalPriceHistoryResponse])
def get_price_history(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Get price change history for eval runbook."""
    runbook = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).first()
    if not runbook:
        raise HTTPException(status_code=404, detail="Eval runbook not found")

    history = (
        db.query(EvalPriceHistory)
        .filter(EvalPriceHistory.eval_runbook_id == runbook.id)
        .order_by(EvalPriceHistory.changed_at.desc())
        .all()
    )

    return history
