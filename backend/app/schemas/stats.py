"""Statistics schemas."""

from pydantic import BaseModel, Field


class PrimaryCounts(BaseModel):
    """Primary collection counts and values."""

    count: int
    volumes: int
    value_low: float
    value_mid: float
    value_high: float


class SimpleCounts(BaseModel):
    """Simple count wrapper."""

    count: int


class WeekDelta(BaseModel):
    """Week-over-week changes."""

    count: int
    volumes: int
    value_mid: float
    authenticated_bindings: int


class OverviewStats(BaseModel):
    """Collection overview statistics."""

    primary: PrimaryCounts
    extended: SimpleCounts
    flagged: SimpleCounts
    total_items: int
    authenticated_bindings: int
    in_transit: int
    week_delta: WeekDelta


class BinderData(BaseModel):
    """Authenticated binding data by binder."""

    binder_id: int
    binder: str
    full_name: str | None
    count: int
    value: float
    founded_year: int | None = None
    closed_year: int | None = None
    sample_titles: list[str] = Field(default_factory=list)
    has_more: bool = False


class EraData(BaseModel):
    """Books grouped by era."""

    era: str
    count: int
    value: float


class PublisherData(BaseModel):
    """Books grouped by publisher."""

    publisher_id: int
    publisher: str
    tier: str | None
    count: int
    value: float
    volumes: int


class AuthorData(BaseModel):
    """Books grouped by author."""

    author_id: int
    author: str
    count: int
    value: float
    volumes: int
    total_volumes: int = Field(default=0, description="Same as volumes, for backward compat")
    titles: int = Field(description="Number of distinct book records")
    sample_titles: list[str] = Field(default_factory=list)
    has_more: bool = False
    era: str | None = None
    birth_year: int | None = None
    death_year: int | None = None


class PublisherDataExtended(BaseModel):
    """Books grouped by publisher with extended metadata."""

    publisher_id: int
    publisher: str
    tier: str | None
    count: int
    value: float
    volumes: int
    description: str | None = None
    founded_year: int | None = None


class EraDefinition(BaseModel):
    """Era definition with label, year range, and description."""

    label: str
    years: str
    description: str


class ConditionDefinition(BaseModel):
    """Condition grade definition with label and description."""

    label: str
    description: str


class ReferenceDefinitions(BaseModel):
    """Reference data definitions for UI display."""

    eras: dict[str, EraDefinition]
    conditions: dict[str, ConditionDefinition]


class AcquisitionDay(BaseModel):
    """Daily acquisition data."""

    date: str
    label: str
    count: int
    value: float
    cost: float
    cumulative_count: int
    cumulative_value: float
    cumulative_cost: float


class ConditionData(BaseModel):
    """Books grouped by condition grade."""

    condition: str
    count: int
    value: float


class CategoryData(BaseModel):
    """Books grouped by category."""

    category: str
    count: int
    value: float


class DashboardResponse(BaseModel):
    """Complete dashboard statistics response."""

    overview: OverviewStats
    bindings: list[BinderData]
    by_era: list[EraData]
    by_publisher: list[PublisherDataExtended]
    by_author: list[AuthorData]
    acquisitions_daily: list[AcquisitionDay]
    by_condition: list[ConditionData]
    by_category: list[CategoryData]
    # Reference definitions for UI display (single source of truth)
    references: ReferenceDefinitions | None = None
