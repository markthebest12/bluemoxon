"""Binder model - Authenticated binding houses."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Binder(Base):
    """Authenticated binding house (Zaehnsdorf, Riviere, etc.)."""

    __tablename__ = "binders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str | None] = mapped_column(String(20))  # TIER_1, TIER_2, or null
    full_name: Mapped[str | None] = mapped_column(String(200))
    authentication_markers: Mapped[str | None] = mapped_column(Text)
    preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    closed_year: Mapped[int | None] = mapped_column(Integer)  # null if still operating

    # Relationships
    books = relationship("Book", back_populates="binder")
