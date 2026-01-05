"""Publisher alias model for name variant mappings."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PublisherAlias(Base):
    """Maps publisher name variants to canonical publishers."""

    __tablename__ = "publisher_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    publisher_id: Mapped[int] = mapped_column(
        ForeignKey("publishers.id", ondelete="CASCADE"), nullable=False
    )

    publisher = relationship("Publisher", back_populates="aliases")
