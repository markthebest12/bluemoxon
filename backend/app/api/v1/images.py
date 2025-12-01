"""Book Images API endpoints."""

import os
import shutil
import uuid
from pathlib import Path

import boto3
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Book, BookImage

# Thumbnail settings
THUMBNAIL_SIZE = (300, 300)  # Max width/height for thumbnails
THUMBNAIL_QUALITY = 85  # JPEG quality for thumbnails

router = APIRouter()

# Get settings
settings = get_settings()

# Local storage path for development
LOCAL_IMAGES_PATH = Path(settings.local_images_path)

# Placeholder image path
PLACEHOLDER_PATH = LOCAL_IMAGES_PATH / "placeholder.jpg"

# S3 prefix for book images
S3_IMAGES_PREFIX = "books/"

# CloudFront CDN URL for images (production only)
CLOUDFRONT_CDN_URL = "https://bluemoxon.com/book-images"


def is_production() -> bool:
    """Check if we're running in production (AWS Lambda)."""
    return settings.database_secret_arn is not None


def get_cloudfront_url(s3_key: str, is_thumbnail: bool = False) -> str:
    """Get the CloudFront CDN URL for an image.

    Args:
        s3_key: The S3 key (filename) of the image
        is_thumbnail: If True, returns the thumbnail URL

    Returns:
        Full CloudFront URL for the image
    """
    if is_thumbnail:
        s3_key = get_thumbnail_key(s3_key)
    return f"{CLOUDFRONT_CDN_URL}/{S3_IMAGES_PREFIX}{s3_key}"


def get_s3_client():
    """Get S3 client using Lambda's AWS_REGION env var."""
    # Lambda automatically sets AWS_REGION to the function's region
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("s3", region_name=region)


def ensure_images_dir():
    """Ensure images directory exists."""
    LOCAL_IMAGES_PATH.mkdir(parents=True, exist_ok=True)


def generate_thumbnail(image_path: Path, thumbnail_path: Path) -> bool:
    """Generate a thumbnail from an image file.

    Args:
        image_path: Path to the original image
        thumbnail_path: Path where thumbnail should be saved

    Returns:
        True if thumbnail was created successfully, False otherwise
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Create thumbnail maintaining aspect ratio
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Save as JPEG for consistent format and smaller size
            img.save(thumbnail_path, "JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            return True
    except Exception:
        return False


def get_thumbnail_key(s3_key: str) -> str:
    """Get the S3 key for a thumbnail from the original image key.

    Example: 'book_123_abc.jpg' -> 'thumb_book_123_abc.jpg'
    """
    return f"thumb_{s3_key}"


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

    images = (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id)
        .order_by(BookImage.display_order)
        .all()
    )

    base_url = get_api_base_url()

    result = []
    for img in images:
        if is_production():
            # Use CloudFront CDN URLs for caching
            # Note: thumbnails not yet in S3, use full image as fallback
            url = get_cloudfront_url(img.s3_key)
            thumbnail_url = url  # Full image until thumbnails are generated
        else:
            # Use API endpoints for local development
            url = f"{base_url}/api/v1/books/{book_id}/images/{img.id}/file"
            thumbnail_url = f"{base_url}/api/v1/books/{book_id}/images/{img.id}/thumbnail"

        result.append(
            {
                "id": img.id,
                "s3_key": img.s3_key,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "image_type": img.image_type,
                "display_order": img.display_order,
                "is_primary": img.is_primary,
                "caption": img.caption,
            }
        )

    return result


@router.get("/primary")
def get_primary_image(book_id: int, db: Session = Depends(get_db)):
    """Get the primary (thumbnail) image for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Try to find primary image
    image = (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id, BookImage.is_primary.is_(True))
        .first()
    )

    # If no primary, get first image by display order
    if not image:
        image = (
            db.query(BookImage)
            .filter(BookImage.book_id == book_id)
            .order_by(BookImage.display_order)
            .first()
        )

    base_url = get_api_base_url()

    if image:
        if is_production():
            # Use CloudFront CDN URLs for caching
            # Note: thumbnails not yet in S3, use full image as fallback
            url = get_cloudfront_url(image.s3_key)
            thumbnail_url = url  # Full image until thumbnails are generated
        else:
            # Use API endpoints for local development
            url = f"{base_url}/api/v1/books/{book_id}/images/{image.id}/file"
            thumbnail_url = f"{base_url}/api/v1/books/{book_id}/images/{image.id}/thumbnail"

        return {
            "id": image.id,
            "url": url,
            "thumbnail_url": thumbnail_url,
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
    """Serve the actual image file or redirect to CloudFront/S3."""
    from fastapi.responses import RedirectResponse

    image = (
        db.query(BookImage).filter(BookImage.id == image_id, BookImage.book_id == book_id).first()
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if is_production():
        # In production, redirect to CloudFront CDN URL (cached)
        cloudfront_url = get_cloudfront_url(image.s3_key)
        return RedirectResponse(url=cloudfront_url, status_code=302)
    else:
        # For local development, serve from local path
        file_path = LOCAL_IMAGES_PATH / image.s3_key
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")

        return FileResponse(file_path)


@router.get("/{image_id}/thumbnail")
def get_image_thumbnail(book_id: int, image_id: int, db: Session = Depends(get_db)):
    """Serve thumbnail version of the image."""
    from fastapi.responses import RedirectResponse

    image = (
        db.query(BookImage).filter(BookImage.id == image_id, BookImage.book_id == book_id).first()
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    thumbnail_key = get_thumbnail_key(image.s3_key)

    if is_production():
        # In production, redirect to CloudFront CDN URL (cached)
        # CloudFront will return 404 if thumbnail doesn't exist, which is acceptable
        cloudfront_url = get_cloudfront_url(image.s3_key, is_thumbnail=True)
        return RedirectResponse(url=cloudfront_url, status_code=302)
    else:
        # For local development, serve thumbnail from local path
        thumbnail_path = LOCAL_IMAGES_PATH / thumbnail_key

        # If thumbnail doesn't exist, try to generate it
        if not thumbnail_path.exists():
            original_path = LOCAL_IMAGES_PATH / image.s3_key
            if original_path.exists():
                generate_thumbnail(original_path, thumbnail_path)

        # If thumbnail still doesn't exist, fall back to original
        if not thumbnail_path.exists():
            file_path = LOCAL_IMAGES_PATH / image.s3_key
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Image file not found")
            return FileResponse(file_path)

        return FileResponse(thumbnail_path)


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

    # Generate thumbnail
    thumbnail_name = get_thumbnail_key(unique_name)
    thumbnail_path = LOCAL_IMAGES_PATH / thumbnail_name
    generate_thumbnail(file_path, thumbnail_path)

    # If this is primary, unset any existing primary
    if is_primary:
        db.query(BookImage).filter(
            BookImage.book_id == book_id, BookImage.is_primary.is_(True)
        ).update({BookImage.is_primary: False})

    # Get next display order
    max_order = db.query(BookImage).filter(BookImage.book_id == book_id).count()

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
    image = (
        db.query(BookImage).filter(BookImage.id == image_id, BookImage.book_id == book_id).first()
    )

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
                BookImage.is_primary.is_(True),
                BookImage.id != image_id,
            ).update({BookImage.is_primary: False})
        image.is_primary = is_primary

    db.commit()
    db.refresh(image)

    return {"message": "Image updated", "id": image.id}


@router.delete("/{image_id}", status_code=204)
def delete_image(book_id: int, image_id: int, db: Session = Depends(get_db)):
    """Delete an image."""
    image = (
        db.query(BookImage).filter(BookImage.id == image_id, BookImage.book_id == book_id).first()
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete file and thumbnail
    file_path = LOCAL_IMAGES_PATH / image.s3_key
    if file_path.exists():
        file_path.unlink()

    thumbnail_path = LOCAL_IMAGES_PATH / get_thumbnail_key(image.s3_key)
    if thumbnail_path.exists():
        thumbnail_path.unlink()

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
