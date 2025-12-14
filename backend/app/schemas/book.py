"""Book schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import PaginatedResponse


class BookBase(BaseModel):
    """Base book schema."""

    title: str
    publication_date: str | None = None
    edition: str | None = None
    volumes: int = 1
    is_complete: bool = True  # Set is complete (all volumes present)
    category: str | None = None
    inventory_type: str = "PRIMARY"
    binding_type: str | None = None
    binding_authenticated: bool = False
    binding_description: str | None = None
    condition_grade: str | None = None
    condition_notes: str | None = None
    value_low: Decimal | None = None
    value_mid: Decimal | None = None
    value_high: Decimal | None = None
    purchase_price: Decimal | None = None
    purchase_date: date | None = None
    purchase_source: str | None = None
    discount_pct: Decimal | None = None
    roi_pct: Decimal | None = None
    status: str = "ON_HAND"
    notes: str | None = None
    provenance: str | None = None

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
    ship_date: date | None = None

    # Shipment tracking
    tracking_number: str | None = None
    tracking_carrier: str | None = None
    tracking_url: str | None = None

    # Archive tracking
    source_archived_url: str | None = None
    archive_status: str | None = None  # pending, success, failed


class BookCreate(BookBase):
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
    edition: str | None = None
    volumes: int | None = None
    is_complete: bool | None = None
    category: str | None = None
    inventory_type: str | None = None
    binding_type: str | None = None
    binding_authenticated: bool | None = None
    binding_description: str | None = None
    condition_grade: str | None = None
    condition_notes: str | None = None
    value_low: Decimal | None = None
    value_mid: Decimal | None = None
    value_high: Decimal | None = None
    purchase_price: Decimal | None = None
    purchase_date: date | None = None
    purchase_source: str | None = None
    discount_pct: Decimal | None = None
    roi_pct: Decimal | None = None
    status: str | None = None
    notes: str | None = None
    provenance: str | None = None
    source_url: str | None = None
    source_item_id: str | None = None
    estimated_delivery: date | None = None
    source_archived_url: str | None = None
    archive_status: str | None = None


class AuthorSummary(BaseModel):
    """Author summary for book response."""

    id: int
    name: str

    class Config:
        from_attributes = True


class PublisherSummary(BaseModel):
    """Publisher summary for book response."""

    id: int
    name: str
    tier: str | None

    class Config:
        from_attributes = True


class BinderSummary(BaseModel):
    """Binder summary for book response."""

    id: int
    name: str

    class Config:
        from_attributes = True


class BookResponse(BookBase):
    """Book response schema."""

    id: int
    author: AuthorSummary | None = None
    publisher: PublisherSummary | None = None
    binder: BinderSummary | None = None
    year_start: int | None = None
    year_end: int | None = None
    has_analysis: bool = False
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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class DuplicateCheckResponse(BaseModel):
    """Response for duplicate check."""

    has_duplicates: bool
    matches: list[DuplicateMatch]
