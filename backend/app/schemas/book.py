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


class BookCreate(BookBase):
    """Schema for creating a book."""

    author_id: int | None = None
    publisher_id: int | None = None
    binder_id: int | None = None


class BookUpdate(BaseModel):
    """Schema for updating a book."""

    title: str | None = None
    author_id: int | None = None
    publisher_id: int | None = None
    binder_id: int | None = None
    publication_date: str | None = None
    edition: str | None = None
    volumes: int | None = None
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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookListResponse(PaginatedResponse):
    """Paginated list of books."""

    items: list[BookResponse]
