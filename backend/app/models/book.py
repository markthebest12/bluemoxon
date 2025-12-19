"""Book model - Main entity."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Use TSVECTOR for PostgreSQL, Text for SQLite (testing)
# This allows tests to run with SQLite while production uses PostgreSQL
try:
    from sqlalchemy.dialects.postgresql import TSVECTOR

    SearchVectorType = TSVECTOR
except ImportError:
    pass  # If not PostgreSQL, types not needed


class Book(Base, TimestampMixin):
    """Book entity - represents a single book or set in the collection."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Basic info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"))
    publisher_id: Mapped[int | None] = mapped_column(ForeignKey("publishers.id"))
    binder_id: Mapped[int | None] = mapped_column(ForeignKey("binders.id"))

    # Publication
    publication_date: Mapped[str | None] = mapped_column(String(50))  # "1867-1880" or "1851"
    year_start: Mapped[int | None] = mapped_column(Integer)
    year_end: Mapped[int | None] = mapped_column(Integer)
    edition: Mapped[str | None] = mapped_column(String(100))
    volumes: Mapped[int] = mapped_column(Integer, default=1)
    is_complete: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # Set is complete (all volumes present)

    # Classification
    category: Mapped[str | None] = mapped_column(String(50))
    inventory_type: Mapped[str] = mapped_column(String(20), default="PRIMARY")

    # Binding
    binding_type: Mapped[str | None] = mapped_column(String(50))
    binding_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    binding_description: Mapped[str | None] = mapped_column(Text)

    # Condition
    condition_grade: Mapped[str | None] = mapped_column(String(20))
    condition_notes: Mapped[str | None] = mapped_column(Text)

    # Valuation
    value_low: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    value_mid: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    value_high: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Acquisition
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    acquisition_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2)
    )  # Total paid incl. shipping/tax
    purchase_date: Mapped[date | None] = mapped_column(Date)
    purchase_source: Mapped[str | None] = mapped_column(String(200))
    discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))  # Up to 9999.99%
    roi_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))  # Up to 99999.99%

    # Status: EVALUATING, IN_TRANSIT, ON_HAND, SOLD, REMOVED, CANCELED
    status: Mapped[str] = mapped_column(String(20), default="ON_HAND")

    # Source tracking
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_item_id: Mapped[str | None] = mapped_column(String(100))

    # Delivery tracking
    estimated_delivery: Mapped[date | None] = mapped_column(Date)
    estimated_delivery_end: Mapped[date | None] = mapped_column(Date)

    # Shipment tracking
    tracking_number: Mapped[str | None] = mapped_column(String(100))
    tracking_carrier: Mapped[str | None] = mapped_column(String(50))
    tracking_url: Mapped[str | None] = mapped_column(String(500))
    tracking_status: Mapped[str | None] = mapped_column(String(100))
    tracking_last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ship_date: Mapped[date | None] = mapped_column(Date)

    # Acquisition scoring (captured at purchase time)
    scoring_snapshot: Mapped[dict | None] = mapped_column(JSON)

    # Archive tracking
    source_archived_url: Mapped[str | None] = mapped_column(String(500))
    archive_status: Mapped[str | None] = mapped_column(String(20))  # pending, success, failed

    # Calculated scores
    investment_grade: Mapped[int | None] = mapped_column(Integer)
    strategic_fit: Mapped[int | None] = mapped_column(Integer)
    collection_impact: Mapped[int | None] = mapped_column(Integer)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    scores_calculated_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[str | None] = mapped_column(Text)

    # Searchable provenance/edition fields (auto-populated by analysis)
    is_first_edition: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    has_provenance: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    provenance_tier: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Legacy reference (for migration)
    legacy_row: Mapped[int | None] = mapped_column(Integer)

    # Full-text search (PostgreSQL only, nullable for SQLite tests)
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    author = relationship("Author", back_populates="books")
    publisher = relationship("Publisher", back_populates="books")
    binder = relationship("Binder", back_populates="books")
    analysis = relationship(
        "BookAnalysis",
        back_populates="book",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    images = relationship(
        "BookImage",
        back_populates="book",
        order_by="BookImage.display_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    analysis_jobs = relationship(
        "AnalysisJob",
        back_populates="book",
        order_by="AnalysisJob.created_at.desc()",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    eval_runbook = relationship(
        "EvalRunbook",
        back_populates="book",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    eval_runbook_jobs = relationship(
        "EvalRunbookJob",
        back_populates="book",
        order_by="EvalRunbookJob.created_at.desc()",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("books_inventory_type_idx", "inventory_type"),
        Index("books_category_idx", "category"),
        Index("books_status_idx", "status"),
        Index("books_source_item_id_idx", "source_item_id"),
    )
