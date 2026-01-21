"""Schemas for image migration endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MigrationRequest(BaseModel):
    """Request to start a migration job."""

    stage: Literal[1, 2, 3] = Field(
        ...,
        description="Migration stage: 1=fix ContentType, 2=copy thumbnails, 3=cleanup",
    )
    dry_run: bool = Field(
        default=True,
        description="If true, only report what would be done without making changes",
    )
    limit: int | None = Field(
        default=None,
        description="Maximum number of objects to process (for testing)",
    )
    batch_size: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Objects to process per request before returning (default 500)",
    )
    continuation_token: str | None = Field(
        default=None,
        description="Token from previous response to resume processing",
    )


class MigrationStats(BaseModel):
    """Statistics from a migration run."""

    processed: int = 0
    fixed: int = 0
    already_correct: int = 0
    copied: int = 0
    already_exists: int = 0
    deleted: int = 0
    versions_deleted: int = 0
    skipped: int = 0
    skipped_not_jpeg: int = 0
    skipped_no_jpg: int = 0
    errors: int = 0


class MigrationError(BaseModel):
    """Error encountered during migration."""

    key: str
    error: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MigrationJob(BaseModel):
    """Status of a migration job."""

    job_id: str
    stage: int
    status: Literal["running", "completed", "failed", "partial"]
    dry_run: bool
    started_at: datetime
    completed_at: datetime | None = None
    stats: MigrationStats = Field(default_factory=MigrationStats)
    errors: list[MigrationError] = Field(default_factory=list)
    continuation_token: str | None = Field(
        default=None,
        description="Token to pass in next request to continue processing. None means complete.",
    )
    has_more: bool = Field(
        default=False,
        description="True if there are more objects to process",
    )
