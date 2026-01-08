"""Eval Runbook Job schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvalRunbookJobResponse(BaseModel):
    """Eval runbook job response schema."""

    job_id: UUID
    book_id: int
    status: str  # pending, running, completed, failed
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, job) -> "EvalRunbookJobResponse":
        """Create response from ORM model with field mapping."""
        return cls(
            job_id=job.id,
            book_id=job.book_id,
            status=job.status,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
        )
