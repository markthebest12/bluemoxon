"""AI connection model — canonical storage for AI-discovered personal connections."""

from sqlalchemy import Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AIConnection(TimestampMixin, Base):
    """Canonical storage for AI-discovered personal connections between entities.

    Connections are stored with canonical ordering: source node ID (as
    ``{type}:{id}`` string) is always less than target node ID.  This
    prevents A→B and B→A being stored as separate rows.  The UNIQUE
    constraint on (source_type, source_id, target_type, target_id,
    relationship) enforces deduplication at the DB level.
    """

    __tablename__ = "ai_connections"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "relationship",
            name="uq_ai_connection",
        ),
        Index("ix_ai_connections_source", "source_type", "source_id"),
        Index("ix_ai_connections_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    relationship: Mapped[str] = mapped_column(String(20), nullable=False)
    sub_type: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    evidence: Mapped[str | None] = mapped_column(Text)
