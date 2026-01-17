"""Image processing job model for async background removal."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ImageProcessingJob(Base):
    """Tracks async image processing jobs."""

    __tablename__ = "image_processing_jobs"
    __table_args__ = (
        Index(
            "ix_image_processing_jobs_pending_unique",
            "book_id",
            "source_image_id",
            unique=True,
            postgresql_where="status IN ('pending', 'processing')",
        ),
        Index(
            "ix_image_processing_jobs_query",
            "book_id",
            "source_image_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    source_image_id: Mapped[int | None] = mapped_column(
        ForeignKey("book_images.id", ondelete="SET NULL"), nullable=True
    )
    processed_image_id: Mapped[int | None] = mapped_column(
        ForeignKey("book_images.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    book = relationship("Book", back_populates="image_processing_jobs")
    source_image = relationship("BookImage", foreign_keys=[source_image_id], lazy="joined")
    processed_image = relationship("BookImage", foreign_keys=[processed_image_id], lazy="joined")
