# backend/app/schemas/social_circles.py

"""Social Circles API schemas.

Defines request/response schemas for the social circles endpoint.
All data is inferred from existing book/author/publisher/binder relationships.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the social network."""

    author = "author"
    publisher = "publisher"
    binder = "binder"


class ConnectionType(str, Enum):
    """Types of connections between nodes."""

    publisher = "publisher"  # Author published by publisher
    shared_publisher = "shared_publisher"  # Two authors share a publisher
    binder = "binder"  # Author's book bound by binder


class Era(str, Enum):
    """Historical eras for categorization."""

    pre_romantic = "pre_romantic"
    romantic = "romantic"
    victorian = "victorian"
    edwardian = "edwardian"
    post_1910 = "post_1910"
    unknown = "unknown"


class SocialCircleNode(BaseModel):
    """A node in the social network graph."""

    id: str = Field(..., description="Node ID (e.g., 'author:42')")
    entity_id: int = Field(..., description="Database entity ID")
    name: str = Field(..., description="Display name")
    type: NodeType = Field(..., description="Node type")

    # Author-specific fields
    birth_year: int | None = Field(None, description="Birth year (authors)")
    death_year: int | None = Field(None, description="Death year (authors)")
    era: Era | None = Field(None, description="Historical era")
    tier: str | None = Field(None, description="Tier classification")

    # Publisher/binder-specific fields
    founded_year: int | None = Field(None, description="Year founded (publishers/binders)")
    closed_year: int | None = Field(None, description="Year closed (publishers/binders)")

    # Collection stats
    book_count: int = Field(..., description="Number of books in collection")
    book_ids: list[int] = Field(default_factory=list, description="Book IDs in collection")


class SocialCircleEdge(BaseModel):
    """An edge (connection) in the social network graph."""

    id: str = Field(..., description="Edge ID (e.g., 'e:author:42:publisher:7')")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: ConnectionType = Field(..., description="Connection type")
    strength: int = Field(
        ..., ge=2, le=10, description="Connection strength (2-10, based on shared works)"
    )
    evidence: str | None = Field(None, description="Evidence for connection")
    shared_book_ids: list[int] | None = Field(None, description="Books connecting these nodes")
    start_year: int | None = Field(None, description="Start of relationship")
    end_year: int | None = Field(None, description="End of relationship")


class SocialCirclesMeta(BaseModel):
    """Metadata about the social circles response."""

    total_books: int = Field(..., description="Total books analyzed")
    total_authors: int = Field(..., description="Total authors in graph")
    total_publishers: int = Field(..., description="Total publishers in graph")
    total_binders: int = Field(..., description="Total binders in graph")
    date_range: tuple[int, int] = Field(..., description="Min/max year range")
    generated_at: datetime = Field(..., description="When data was generated")
    truncated: bool = Field(False, description="True if data was truncated due to limits")


class SocialCirclesResponse(BaseModel):
    """Response schema for the social circles endpoint."""

    nodes: list[SocialCircleNode] = Field(..., description="Graph nodes")
    edges: list[SocialCircleEdge] = Field(..., description="Graph edges")
    meta: SocialCirclesMeta = Field(..., description="Response metadata")
