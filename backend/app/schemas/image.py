"""Image schemas."""

from typing import Literal

from pydantic import BaseModel

ThumbnailStatus = Literal["generated", "failed", "skipped"]


class ImageUploadResponse(BaseModel):
    """Response for image upload endpoint."""

    id: int
    url: str
    thumbnail_url: str | None = None
    image_type: str
    is_primary: bool
    thumbnail_status: ThumbnailStatus
    thumbnail_error: str | None = None
    duplicate: bool = False
    message: str | None = None
