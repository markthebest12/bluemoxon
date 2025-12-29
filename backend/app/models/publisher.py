"""Publisher model."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Publisher(Base):
    """Publisher entity - Tier 1 publishers are premium Victorian publishers."""

    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str | None] = mapped_column(String(10))  # TIER_1, TIER_2, TIER_3, OTHER
    founded_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    books = relationship("Book", back_populates="publisher")
