"""Author model."""

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Author(Base):
    """Author entity."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    death_year: Mapped[int | None] = mapped_column(Integer)
    era: Mapped[str | None] = mapped_column(String(50))  # Victorian, Romantic, etc.
    first_acquired_date: Mapped[date | None] = mapped_column(Date)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    books = relationship("Book", back_populates="author")
