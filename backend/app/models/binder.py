"""Binder model - Authenticated binding houses."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Binder(Base):
    """Authenticated binding house (Zaehnsdorf, Riviere, etc.)."""

    __tablename__ = "binders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    authentication_markers: Mapped[str | None] = mapped_column(Text)

    # Relationships
    books = relationship("Book", back_populates="binder")
