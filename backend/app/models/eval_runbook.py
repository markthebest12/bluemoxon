"""Eval Runbook model - lightweight evaluation report."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EvalRunbook(Base, TimestampMixin):
    """Lightweight evaluation report for acquisition decisions."""

    __tablename__ = "eval_runbooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        unique=True,
    )

    # Scoring
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)  # PASS or ACQUIRE

    # Pricing
    original_asking_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    current_asking_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    discount_code: Mapped[str | None] = mapped_column(String(100))
    price_notes: Mapped[str | None] = mapped_column(Text)
    fmv_low: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    fmv_high: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    recommended_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # FMV Comparables
    ebay_comparables: Mapped[list | None] = mapped_column(JSON)
    abebooks_comparables: Mapped[list | None] = mapped_column(JSON)

    # Content
    condition_grade: Mapped[str | None] = mapped_column(String(20))
    condition_positives: Mapped[list | None] = mapped_column(JSON)
    condition_negatives: Mapped[list | None] = mapped_column(JSON)
    critical_issues: Mapped[list | None] = mapped_column(JSON)
    analysis_narrative: Mapped[str | None] = mapped_column(Text)

    # Item identification (cached from book + listing)
    item_identification: Mapped[dict | None] = mapped_column(JSON)

    # Metadata
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    book = relationship("Book", back_populates="eval_runbook")


class EvalPriceHistory(Base):
    """Track price changes for eval runbooks."""

    __tablename__ = "eval_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    eval_runbook_id: Mapped[int] = mapped_column(
        ForeignKey("eval_runbooks.id", ondelete="CASCADE")
    )
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    discount_code: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    score_before: Mapped[int | None] = mapped_column(Integer)
    score_after: Mapped[int | None] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
