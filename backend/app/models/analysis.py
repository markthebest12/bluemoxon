"""Book Analysis model."""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BookAnalysis(Base, TimestampMixin):
    """Detailed analysis document for a book."""

    __tablename__ = "book_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        unique=True,
    )

    # Parsed sections (JSON for cross-database compatibility)
    executive_summary: Mapped[str | None] = mapped_column(Text)
    condition_assessment: Mapped[dict | None] = mapped_column(JSON)
    binding_elaborateness_tier: Mapped[int | None] = mapped_column(Integer)
    market_analysis: Mapped[dict | None] = mapped_column(JSON)
    historical_significance: Mapped[str | None] = mapped_column(Text)
    recommendations: Mapped[str | None] = mapped_column(Text)
    risk_factors: Mapped[list | None] = mapped_column(JSON)  # Array stored as JSON

    # Original content
    full_markdown: Mapped[str | None] = mapped_column(Text)
    source_filename: Mapped[str | None] = mapped_column(String(500))

    # Extraction status tracking (Stage 2 two-stage extraction)
    # Values: "success" (Stage 2 worked), "degraded" (fell back to YAML parsing),
    #         "failed" (extraction error, no structured data), null (legacy/unknown)
    extraction_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Full-text search (PostgreSQL only, nullable for SQLite tests)
    search_vector: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    book = relationship("Book", back_populates="analysis")
