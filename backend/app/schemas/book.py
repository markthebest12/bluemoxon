"""Book schemas.

Schema inheritance pattern:
- _BookFieldsMixin: Shared non-enum fields (title, dates, notes, etc.)
- BookInputBase: Uses enums for INPUT validation (BookCreate inherits this)
- BookOutputBase: Uses strings for OUTPUT serialization (BookResponse inherits this)
- BookListParams: Uses enums for QUERY PARAM validation (filtering)
- BookUpdate: Uses enums for INPUT validation (explicit Optional fields)

This separation ensures:
1. New data is validated against known enum values (prevents data quality issues)
2. Legacy DB values (e.g., "VG", "Tier 3") serialize without 500 errors
3. No fragile field-type overrides in inheritance chains
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    BookStatus,
    ConditionGrade,
    Era,
    InventoryType,
    SortOrder,
    Tier,
)
from app.schemas.common import PaginatedResponse

# Valid columns for sort_by parameter - prevents sorting by sensitive/internal fields
ValidSortField = Literal[
    "title",
    "created_at",
    "updated_at",
    "publication_date",
    "year_start",
    "year_end",
    "value_low",
    "value_mid",
    "value_high",
    "purchase_price",
    "purchase_date",
    "status",
    "category",
    "condition_grade",
    "author_id",
    "publisher_id",
    "overall_score",
    "investment_grade",
    "strategic_fit",
    "collection_impact",
]


class BookListParams(BaseModel):
    """Query parameters for listing books."""

    # Pagination
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

    # Search
    q: str | None = Field(default=None, description="Search query for title, author, notes")

    # Filters with enum validation
    status: BookStatus | None = None
    inventory_type: InventoryType | None = None
    category: str | None = None  # Too many values for enum
    publisher_id: int | None = None
    publisher_tier: Tier | None = None
    author_id: int | None = None
    binder_id: int | None = None
    binding_authenticated: bool | None = None
    binding_type: str | None = None  # Too many values for enum
    condition_grade: ConditionGrade | None = None
    condition_grade__isnull: bool | None = None  # Filter for NULL condition_grade
    provenance_tier: Tier | None = None
    era: Era | None = None
    category__isnull: bool | None = None  # Filter for NULL category

    # Range filters
    min_value: float | None = None
    max_value: float | None = None
    year_start: int | None = None
    year_end: int | None = None

    # Date filters
    date_acquired: date | None = Field(
        default=None, description="Filter by acquisition date (purchase_date)"
    )

    # Boolean filters
    has_images: bool | None = None
    has_analysis: bool | None = None
    has_provenance: bool | None = None
    is_first_edition: bool | None = None

    # Sorting - restricted to safe, exposed fields
    sort_by: ValidSortField = "title"
    sort_order: SortOrder = SortOrder.ASC


class _BookFieldsMixin(BaseModel):
    """Shared book fields that don't involve enum types.

    This mixin contains all fields that have the same type in both input
    and output schemas. Enum-typed fields are defined separately in
    BookInputBase and BookOutputBase.
    """

    title: str
    publication_date: str | None = None
    edition: str | None = None
    volumes: int = 1
    is_complete: bool = True  # Set is complete (all volumes present)
    category: str | None = None
    binding_type: str | None = None
    binding_authenticated: bool = False
    binding_description: str | None = None
    condition_notes: str | None = None
    value_low: Decimal | None = None
    value_mid: Decimal | None = None
    value_high: Decimal | None = None
    purchase_price: Decimal | None = None
    acquisition_cost: Decimal | None = None  # Total paid incl. shipping/tax
    purchase_date: date | None = None
    purchase_source: str | None = None
    discount_pct: Decimal | None = None
    roi_pct: Decimal | None = None
    notes: str | None = None
    provenance: str | None = None
    is_first_edition: bool | None = None
    has_provenance: bool = False

    # Source tracking
    source_url: str | None = None
    source_item_id: str | None = None

    # Delivery tracking
    estimated_delivery: date | None = None
    estimated_delivery_end: date | None = None

    # Shipment tracking
    tracking_number: str | None = None
    tracking_carrier: str | None = None
    tracking_url: str | None = None
    tracking_status: str | None = None
    tracking_last_checked: datetime | None = None
    ship_date: date | None = None

    # Archive tracking
    source_archived_url: str | None = None
    archive_status: str | None = None  # pending, success, failed


class BookInputBase(_BookFieldsMixin):
    """Base schema for book INPUT (create/update) - uses enums for validation."""

    inventory_type: InventoryType = InventoryType.PRIMARY
    condition_grade: ConditionGrade | None = None
    status: BookStatus = BookStatus.ON_HAND
    provenance_tier: Tier | None = None


class BookOutputBase(_BookFieldsMixin):
    """Base schema for book OUTPUT (responses) - uses strings for legacy compatibility."""

    inventory_type: str = "PRIMARY"
    condition_grade: str | None = None
    status: str = "ON_HAND"
    provenance_tier: str | None = None


# Backward compatibility alias - some code may reference BookBase
BookBase = BookInputBase


class BookCreate(BookInputBase):
    """Schema for creating a book."""

    author_id: int | None = None
    publisher_id: int | None = None
    binder_id: int | None = None

    # S3 keys from listing import (images will be copied to book's folder)
    listing_s3_keys: list[str] | None = None


class BookUpdate(BaseModel):
    """Schema for updating a book."""

    title: str | None = None
    author_id: int | None = None
    publisher_id: int | None = None
    binder_id: int | None = None
    publication_date: str | None = None
    year_start: int | None = None
    year_end: int | None = None
    edition: str | None = None
    volumes: int | None = None
    is_complete: bool | None = None
    category: str | None = None
    inventory_type: InventoryType | None = None
    binding_type: str | None = None
    binding_authenticated: bool | None = None
    binding_description: str | None = None
    condition_grade: ConditionGrade | None = None
    condition_notes: str | None = None
    value_low: Decimal | None = None
    value_mid: Decimal | None = None
    value_high: Decimal | None = None
    purchase_price: Decimal | None = None
    acquisition_cost: Decimal | None = None  # Total paid incl. shipping/tax
    purchase_date: date | None = None
    purchase_source: str | None = None
    discount_pct: Decimal | None = None
    roi_pct: Decimal | None = None
    status: BookStatus | None = None
    notes: str | None = None
    provenance: str | None = None
    is_first_edition: bool | None = None
    has_provenance: bool | None = None
    provenance_tier: Tier | None = None
    source_url: str | None = None
    source_item_id: str | None = None
    estimated_delivery: date | None = None
    source_archived_url: str | None = None
    archive_status: str | None = None


class AuthorSummary(BaseModel):
    """Author summary for book response."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class PublisherSummary(BaseModel):
    """Publisher summary for book response."""

    id: int
    name: str
    tier: str | None

    model_config = ConfigDict(from_attributes=True)


class BinderSummary(BaseModel):
    """Binder summary for book response."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class BookResponse(BookOutputBase):
    """Book response schema.

    Inherits from BookOutputBase which uses string types for enum fields,
    allowing legacy database values (e.g., "VG+", "Tier 3") to serialize
    without validation errors.
    """

    id: int
    author: AuthorSummary | None = None
    publisher: PublisherSummary | None = None
    binder: BinderSummary | None = None
    year_start: int | None = None
    year_end: int | None = None
    era: str | None = (
        None  # Computed field: Pre-Romantic, Romantic, Victorian, Edwardian, Post-1910, Unknown
    )
    has_analysis: bool = False
    has_eval_runbook: bool = False
    eval_runbook_job_status: str | None = None  # pending, running, or None
    analysis_job_status: str | None = None  # pending, running, or None
    analysis_issues: list[str] | None = None  # truncated, degraded, missing_condition, etc.
    # Note: is_first_edition, has_provenance, provenance_tier inherited from BookBase
    image_count: int = 0
    primary_image_url: str | None = None
    scoring_snapshot: dict | None = None
    investment_grade: int | None = None
    strategic_fit: int | None = None
    collection_impact: int | None = None
    overall_score: int | None = None
    scores_calculated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookListResponse(PaginatedResponse):
    """Paginated list of books."""

    items: list[BookResponse]


class AcquireRequest(BaseModel):
    """Request body for acquiring a book (EVALUATING -> IN_TRANSIT)."""

    purchase_price: Decimal
    purchase_date: date
    order_number: str
    place_of_purchase: str
    estimated_delivery: date | None = None
    tracking_number: str | None = None
    tracking_carrier: str | None = None
    tracking_url: str | None = None


class ScoringSnapshot(BaseModel):
    """Scoring data captured at acquisition time."""

    captured_at: datetime
    purchase_price: Decimal
    fmv_at_purchase: dict  # {"low": x, "mid": y, "high": z}
    discount_pct: Decimal
    investment_grade: Decimal
    strategic_fit: dict  # {"score": x, "max": y, "criteria": [...]}
    collection_position: dict  # {"items_before": x, "volumes_before": y}


class TrackingRequest(BaseModel):
    """Request body for adding shipment tracking."""

    tracking_number: str | None = None
    tracking_carrier: str | None = None
    tracking_url: str | None = None


class DuplicateCheckRequest(BaseModel):
    """Request body for checking duplicate books."""

    title: str
    author_id: int | None = None


class DuplicateMatch(BaseModel):
    """A potential duplicate book match."""

    id: int
    title: str
    author_name: str | None
    status: str
    similarity_score: float

    model_config = ConfigDict(from_attributes=True)


class DuplicateCheckResponse(BaseModel):
    """Response for duplicate check."""

    has_duplicates: bool
    matches: list[DuplicateMatch]


class BookSpotlightItem(BaseModel):
    """Lightweight book item for Collection Spotlight feature.

    Contains only fields needed for spotlight display, optimized for performance.
    """

    id: int
    title: str
    author_name: str | None = None
    value_mid: Decimal | None = None
    primary_image_url: str | None = None
    binder_name: str | None = None
    binding_authenticated: bool = False

    model_config = ConfigDict(from_attributes=True)
