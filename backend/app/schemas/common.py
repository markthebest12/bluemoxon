"""Common schemas."""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Base paginated response."""

    total: int
    page: int
    per_page: int
    pages: int
