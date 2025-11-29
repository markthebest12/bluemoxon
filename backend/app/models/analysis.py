"""Book Analysis model."""

from sqlalchemy import String, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB, ARRAY
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

    # Parsed sections
    executive_summary: Mapped[str | None] = mapped_column(Text)
    condition_assessment: Mapped[dict | None] = mapped_column(JSONB)
    binding_elaborateness_tier: Mapped[int | None] = mapped_column(Integer)
    market_analysis: Mapped[dict | None] = mapped_column(JSONB)
    historical_significance: Mapped[str | None] = mapped_column(Text)
    recommendations: Mapped[str | None] = mapped_column(Text)
    risk_factors: Mapped[list | None] = mapped_column(ARRAY(String))

    # Original content
    full_markdown: Mapped[str | None] = mapped_column(Text)
    source_filename: Mapped[str | None] = mapped_column(String(500))

    # Full-text search
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    # Relationships
    book = relationship("Book", back_populates="analysis")

    __table_args__ = (
        Index("analyses_search_idx", "search_vector", postgresql_using="gin"),
    )
