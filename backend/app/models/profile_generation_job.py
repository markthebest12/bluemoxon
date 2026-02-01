"""Profile generation job model -- tracks async batch profile generation."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class JobStatus:
    """Status constants for profile generation jobs."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    ACTIVE = (PENDING, IN_PROGRESS)
    TERMINAL = (COMPLETED, FAILED, CANCELLED)


class ProfileGenerationJob(TimestampMixin, Base):
    """Tracks progress of async batch profile generation."""

    __tablename__ = "profile_generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=JobStatus.PENDING)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_entities: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_log: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
