"""Pydantic schemas for entity profile endpoints."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    author = "author"
    publisher = "publisher"
    binder = "binder"


class BiographicalFact(BaseModel):
    """A single biographical fact / gossip item."""

    text: str = Field(..., description="The story (1-2 sentences)")
    year: int | None = Field(None, description="Year the event occurred")
    significance: str = Field(..., description="revelation, notable, or context")
    tone: str = Field(..., description="dramatic, scandalous, tragic, intellectual, or triumphant")
    display_in: list[str] = Field(
        default_factory=list, description="hero-bio, timeline, hover-tooltip"
    )


class RelationshipNarrative(BaseModel):
    """Full relationship story for a high-impact connection."""

    summary: str = Field(..., description="One-line summary for card display")
    details: list[BiographicalFact] = Field(default_factory=list, description="Story facts")
    narrative_style: str = Field(
        "prose-paragraph",
        description="prose-paragraph, bullet-facts, or timeline-events",
    )


class ProfileEntity(BaseModel):
    """Entity summary in profile response."""

    id: int
    type: EntityType
    name: str
    birth_year: int | None = None
    death_year: int | None = None
    founded_year: int | None = None
    closed_year: int | None = None
    era: str | None = None
    tier: str | None = None


class ProfileData(BaseModel):
    """AI-generated profile content."""

    bio_summary: str | None = None
    personal_stories: list[BiographicalFact] = Field(default_factory=list)
    is_stale: bool = False
    generated_at: datetime | None = None
    model_version: str | None = None


class ProfileBook(BaseModel):
    """A book in the entity's collection."""

    id: int
    title: str
    year: int | None = None
    condition: str | None = None
    edition: str | None = None


class ProfileConnection(BaseModel):
    """A connection to another entity."""

    entity: ProfileEntity
    connection_type: str
    strength: int
    shared_book_count: int
    shared_books: list[ProfileBook] = Field(default_factory=list)
    narrative: str | None = None
    narrative_trigger: str | None = None
    is_key: bool = False
    relationship_story: RelationshipNarrative | None = None


class ProfileStats(BaseModel):
    """Collection statistics for this entity."""

    total_books: int = 0
    total_estimated_value: float | None = None
    first_editions: int = 0
    date_range: list[int] = Field(default_factory=list)


class EntityProfileResponse(BaseModel):
    """Full entity profile response."""

    entity: ProfileEntity
    profile: ProfileData
    connections: list[ProfileConnection] = Field(default_factory=list)
    books: list[ProfileBook] = Field(default_factory=list)
    stats: ProfileStats
