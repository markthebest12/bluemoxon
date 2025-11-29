"""Schemas for reference entities (authors, publishers, binders)."""

from datetime import date

from pydantic import BaseModel


# Author schemas
class AuthorCreate(BaseModel):
    """Schema for creating an author."""

    name: str
    birth_year: int | None = None
    death_year: int | None = None
    era: str | None = None
    first_acquired_date: date | None = None


class AuthorUpdate(BaseModel):
    """Schema for updating an author."""

    name: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    era: str | None = None
    first_acquired_date: date | None = None


class AuthorResponse(BaseModel):
    """Author response schema."""

    id: int
    name: str
    birth_year: int | None = None
    death_year: int | None = None
    era: str | None = None
    first_acquired_date: date | None = None
    book_count: int = 0

    class Config:
        from_attributes = True


# Publisher schemas
class PublisherCreate(BaseModel):
    """Schema for creating a publisher."""

    name: str
    tier: str | None = None
    founded_year: int | None = None
    description: str | None = None


class PublisherUpdate(BaseModel):
    """Schema for updating a publisher."""

    name: str | None = None
    tier: str | None = None
    founded_year: int | None = None
    description: str | None = None


class PublisherResponse(BaseModel):
    """Publisher response schema."""

    id: int
    name: str
    tier: str | None = None
    founded_year: int | None = None
    description: str | None = None
    book_count: int = 0

    class Config:
        from_attributes = True


# Binder schemas
class BinderCreate(BaseModel):
    """Schema for creating a binder."""

    name: str
    full_name: str | None = None
    authentication_markers: str | None = None


class BinderUpdate(BaseModel):
    """Schema for updating a binder."""

    name: str | None = None
    full_name: str | None = None
    authentication_markers: str | None = None


class BinderResponse(BaseModel):
    """Binder response schema."""

    id: int
    name: str
    full_name: str | None = None
    authentication_markers: str | None = None
    book_count: int = 0

    class Config:
        from_attributes = True
