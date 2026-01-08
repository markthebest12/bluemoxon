"""Eval Runbook schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ScoreBreakdownItem(BaseModel):
    """Individual scoring criterion."""

    points: int
    notes: str


class FMVComparable(BaseModel):
    """A comparable listing for FMV calculation."""

    title: str
    price: Decimal | None = None  # Can be None if extraction failed
    condition: str | None = None
    days_ago: int | None = None  # For eBay sold


class EvalRunbookBase(BaseModel):
    """Base eval runbook schema."""

    total_score: int
    score_breakdown: dict[str, ScoreBreakdownItem]
    recommendation: str = Field(pattern="^(PASS|ACQUIRE)$")

    # Pricing
    original_asking_price: Decimal | None = None
    current_asking_price: Decimal | None = None
    discount_code: str | None = None
    price_notes: str | None = None
    fmv_low: Decimal | None = None
    fmv_high: Decimal | None = None
    fmv_notes: str | None = None
    fmv_confidence: str | None = None  # "high", "medium", "low"
    recommended_price: Decimal | None = None

    # Tiered recommendation fields
    recommendation_tier: str | None = None  # STRONG_BUY, BUY, CONDITIONAL, PASS
    quality_score: int | None = None  # 0-100
    strategic_fit_score: int | None = None  # 0-100
    combined_score: int | None = None  # Weighted average
    price_position: str | None = None  # EXCELLENT, GOOD, FAIR, POOR
    suggested_offer: Decimal | None = None  # For CONDITIONAL recommendations
    recommendation_reasoning: str | None = None  # 1-2 sentence explanation
    strategic_floor_applied: bool = False
    quality_floor_applied: bool = False
    scoring_version: str = "2025-01"
    score_source: str = "eval_runbook"  # "eval_runbook" or "napoleon"
    last_scored_price: Decimal | None = None

    # Napoleon Analysis override fields
    napoleon_recommendation: str | None = None
    napoleon_reasoning: str | None = None
    napoleon_analyzed_at: datetime | None = None

    # Comparables
    ebay_comparables: list[FMVComparable] | None = None
    abebooks_comparables: list[FMVComparable] | None = None

    # Content
    condition_grade: str | None = None
    condition_positives: list[str] | None = None
    condition_negatives: list[str] | None = None
    critical_issues: list[str] | None = None
    analysis_narrative: str | None = None
    item_identification: dict | None = None


class EvalRunbookResponse(EvalRunbookBase):
    """Eval runbook response schema."""

    id: int
    book_id: int
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvalRunbookPriceUpdate(BaseModel):
    """Schema for updating eval runbook price."""

    new_price: Decimal
    discount_code: str | None = None
    notes: str | None = None


class EvalRunbookPriceUpdateResponse(BaseModel):
    """Response after price update with recalculated score."""

    previous_price: Decimal | None
    new_price: Decimal
    score_before: int
    score_after: int
    recommendation_before: str
    recommendation_after: str
    runbook: EvalRunbookResponse


class EvalPriceHistoryResponse(BaseModel):
    """Price history entry response."""

    id: int
    previous_price: Decimal | None
    new_price: Decimal | None
    discount_code: str | None
    notes: str | None
    score_before: int | None
    score_after: int | None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvalRunbookRefreshResponse(BaseModel):
    """Response after refresh with full AI analysis."""

    status: str  # "completed" or "failed"
    score_before: int | None
    score_after: int
    message: str
    runbook: EvalRunbookResponse
