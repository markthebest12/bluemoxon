"""Book Images API endpoints."""

import io
import os
import shutil
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Book, BookImage

router = APIRouter()

# Get settings
settings = get_settings()

# Local storage path for development
LOCAL_IMAGES_PATH = Path(settings.local_images_path)

# Placeholder image path
PLACEHOLDER_PATH = LOCAL_IMAGES_PATH / "placeholder.jpg"

# S3 prefix for book images
S3_IMAGES_PREFIX = "books/"


def is_production() -> bool:
    """Check if we're running in production (AWS Lambda)."""
    return settings.database_secret_arn is not None


def get_s3_client():
    """Get S3 client using Lambda's AWS_REGION env var."""
    # Lambda automatically sets AWS_REGION to the function's region
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("s3", region_name=region)


def ensure_images_dir():
    """Ensure images directory exists."""
    LOCAL_IMAGES_PATH.mkdir(parents=True, exist_ok=True)


def get_api_base_url() -> str:
    """Get the API base URL for constructing absolute URLs."""
    if is_production():
        return "https://api.bluemoxon.com"
    return ""  # Relative URLs for local dev


@router.get("")
def list_book_images(book_id: int, db: Session = Depends(get_db)):
    """List all images for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    images = db.query(BookImage).filter(
        BookImage.book_id == book_id
    ).order_by(BookImage.display_order).all()

    base_url = get_api_base_url()

    return [
        {
            "id": img.id,
            "s3_key": img.s3_key,
            "url": f"{base_url}/api/v1/books/{book_id}/images/{img.id}/file",
            "thumbnail_url": f"{base_url}/api/v1/books/{book_id}/images/{img.id}/thumbnail",
            "image_type": img.image_type,
            "display_order": img.display_order,
            "is_primary": img.is_primary,
            "caption": img.caption,
        }
        for img in images
    ]


@router.get("/primary")
def get_primary_image(book_id: int, db: Session = Depends(get_db)):
    """Get the primary (thumbnail) image for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Try to find primary image
    image = db.query(BookImage).filter(
        BookImage.book_id == book_id,
        BookImage.is_primary .is_(True)
    ).first()

    # If no primary, get first image by display order
    if not image:
        image = db.query(BookImage).filter(
            BookImage.book_id == book_id
        ).order_by(BookImage.display_order).first()

    base_url = get_api_base_url()

    if image:
        return {
            "id": image.id,
            "url": f"{base_url}/api/v1/books/{book_id}/images/{image.id}/file",
            "thumbnail_url": f"{base_url}/api/v1/books/{book_id}/images/{image.id}/thumbnail",
            "image_type": image.image_type,
            "caption": image.caption,
        }

    # Return placeholder info
    return {
        "id": None,
        "url": f"{base_url}/api/v1/images/placeholder",
        "thumbnail_url": f"{base_url}/api/v1/images/placeholder",
        "image_type": "placeholder",
        "caption": "No image available",
    }


@router.get("/{image_id}/file")
def get_image_file(book_id: int, image_id: int, db: Session = Depends(get_db)):
    """Serve the actual image file or redirect to S3."""
    from fastapi.responses import RedirectResponse

    image = db.query(BookImage).filter(
        BookImage.id == image_id,
        BookImage.book_id == book_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if is_production():
        # In production, redirect to presigned S3 URL
        try:
            s3 = get_s3_client()
            s3_key = S3_IMAGES_PREFIX + image.s3_key

            # Generate presigned URL (valid for 1 hour)
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.images_bucket, "Key": s3_key},
                ExpiresIn=3600,
            )

            return RedirectResponse(url=presigned_url, status_code=302)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise HTTPException(status_code=404, detail="Image file not found in S3")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # For local development, serve from local path
        file_path = LOCAL_IMAGES_PATH / image.s3_key
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")

        return FileResponse(file_path)


@router.get("/{image_id}/thumbnail")
def get_image_thumbnail(book_id: int, image_id: int, db: Session = Depends(get_db)):
    """Serve thumbnail version (for now, same as full image)."""
    # TODO: Implement actual thumbnail generation
    return get_image_file(book_id, image_id, db)


@router.post("", status_code=201)
async def upload_image(
    book_id: int,
    file: UploadFile = File(...),
    image_type: str = Query(default="detail"),
    is_primary: bool = Query(default=False),
    caption: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """Upload a new image for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    ensure_images_dir()

    # Generate unique filename
    ext = Path(file.filename).suffix or ".jpg"
    unique_name = f"{book_id}_{uuid.uuid4().hex}{ext}"
    file_path = LOCAL_IMAGES_PATH / unique_name

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # If this is primary, unset any existing primary
    if is_primary:
        db.query(BookImage).filter(
            BookImage.book_id == book_id,
            BookImage.is_primary .is_(True)
        ).update({BookImage.is_primary: False})

    # Get next display order
    max_order = db.query(BookImage).filter(
        BookImage.book_id == book_id
    ).count()

    # Create database record
    image = BookImage(
        book_id=book_id,
        s3_key=unique_name,
        image_type=image_type,
        display_order=max_order,
        is_primary=is_primary,
        caption=caption,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return {
        "id": image.id,
        "url": f"/api/v1/books/{book_id}/images/{image.id}/file",
        "thumbnail_url": f"/api/v1/books/{book_id}/images/{image.id}/thumbnail",
        "image_type": image.image_type,
        "is_primary": image.is_primary,
    }


@router.put("/{image_id}")
def update_image(
    book_id: int,
    image_id: int,
    image_type: str = Query(default=None),
    is_primary: bool = Query(default=None),
    caption: str = Query(default=None),
    display_order: int = Query(default=None),
    db: Session = Depends(get_db),
):
    """Update image metadata."""
    image = db.query(BookImage).filter(
        BookImage.id == image_id,
        BookImage.book_id == book_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if image_type is not None:
        image.image_type = image_type
    if caption is not None:
        image.caption = caption
    if display_order is not None:
        image.display_order = display_order

    if is_primary is not None:
        if is_primary:
            # Unset any existing primary
            db.query(BookImage).filter(
                BookImage.book_id == book_id,
                BookImage.is_primary .is_(True),
                BookImage.id != image_id
            ).update({BookImage.is_primary: False})
        image.is_primary = is_primary

    db.commit()
    db.refresh(image)

    return {"message": "Image updated", "id": image.id}


@router.delete("/{image_id}", status_code=204)
def delete_image(book_id: int, image_id: int, db: Session = Depends(get_db)):
    """Delete an image."""
    image = db.query(BookImage).filter(
        BookImage.id == image_id,
        BookImage.book_id == book_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete file
    file_path = LOCAL_IMAGES_PATH / image.s3_key
    if file_path.exists():
        file_path.unlink()

    # Delete record
    db.delete(image)
    db.commit()


# Standalone placeholder endpoint (not book-specific)
@router.get("/placeholder", include_in_schema=False)
def get_placeholder_image():
    """Serve placeholder image for books without images."""
    if PLACEHOLDER_PATH.exists():
        return FileResponse(PLACEHOLDER_PATH)

    # Return a simple 1x1 gray pixel if no placeholder exists
    raise HTTPException(status_code=404, detail="Placeholder not configured")
