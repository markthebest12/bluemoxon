"""Cleanup Job model for tracking async cleanup operations."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CleanupJob(Base):
    """Track async cleanup jobs with progress."""

    __tablename__ = "cleanup_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, running, completed, failed

    # Totals from scan
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Progress
    deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @property
    def progress_pct(self) -> float:
        """Calculate progress percentage."""
        if self.total_count == 0:
            return 0.0
        return round(self.deleted_count / self.total_count * 100, 1)
