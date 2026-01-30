"""Entity profile model — caches AI-generated biographical content."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EntityProfile(Base):
    """Cached AI-generated profile for an entity (author, publisher, binder)."""

    __tablename__ = "entity_profiles"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "owner_id", name="uq_entity_profile"),
        Index("idx_entity_profiles_lookup", "entity_type", "entity_id", "owner_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    bio_summary: Mapped[str | None] = mapped_column(Text)
    personal_stories: Mapped[dict | None] = mapped_column(JSON, default=list)
    connection_narratives: Mapped[dict | None] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    model_version: Mapped[str | None] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
