"""Analysis schemas."""

from datetime import datetime

from pydantic import BaseModel


class AnalysisBase(BaseModel):
    """Base analysis schema."""

    executive_summary: str | None = None
    condition_assessment: dict | None = None
    binding_elaborateness_tier: int | None = None
    market_analysis: dict | None = None
    historical_significance: str | None = None
    recommendations: str | None = None
    risk_factors: list[str] | None = None


class AnalysisUpdate(BaseModel):
    """Schema for updating analysis."""

    full_markdown: str


class AnalysisResponse(AnalysisBase):
    """Analysis response schema."""

    id: int
    book_id: int
    full_markdown: str | None = None
    source_filename: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
