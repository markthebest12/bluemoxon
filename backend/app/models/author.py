"""Author model."""

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Author(Base):
    """Author entity."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    death_year: Mapped[int | None] = mapped_column(Integer)
    era: Mapped[str | None] = mapped_column(String(50))  # Victorian, Romantic, etc.
    first_acquired_date: Mapped[date | None] = mapped_column(Date)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str | None] = mapped_column(String(10))  # TIER_1, TIER_2, TIER_3
    preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    books = relationship("Book", back_populates="author")
