"""Book Images API endpoints."""

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.config import get_settings
from app.db import get_db
from app.models import Book, BookImage
from app.schemas.image import ImageUploadResponse
from app.services.aws_clients import get_s3_client
from app.services.image_processing import queue_image_processing
from app.utils.cdn import S3_IMAGES_PREFIX, get_cloudfront_url
from app.utils.image_utils import (
    MIN_DETECTION_BYTES,
    ImageFormat,
    detect_format,
    get_content_type,
    get_extension,
    get_thumbnail_key,
)

# Module logger
logger = logging.getLogger(__name__)

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


def ensure_images_dir():
    """Ensure images directory exists."""
    LOCAL_IMAGES_PATH.mkdir(parents=True, exist_ok=True)


def generate_thumbnail(image_path: Path, thumbnail_path: Path) -> tuple[bool, str]:
    """Generate a thumbnail from an image file.

    Args:
        image_path: Path to the original image
        thumbnail_path: Path where thumbnail should be saved

    Returns:
        Tuple of (success, error_message). error_message is empty on success.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        if not image_path.exists():
            return False, f"Source not found: {image_path}"

        with Image.open(image_path) as img:
            logger.info(f"Thumbnail: {image_path} mode={img.mode} size={img.size}")

            # Apply EXIF orientation to fix sideways images
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Create thumbnail maintaining aspect ratio
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Ensure parent directory exists
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as JPEG for consistent format and smaller size
            img.save(thumbnail_path, "JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            return True, ""
    except Exception as e:
        logger.error(f"Thumbnail failed for {image_path}: {e}")
        return False, str(e)


def get_api_base_url() -> str:
    """Get the API base URL for constructing absolute URLs."""
    if settings.is_production:
        return "https://api.bluemoxon.com"
    elif settings.is_aws_lambda:
        return "https://staging.api.bluemoxon.com"
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
        if settings.is_aws_lambda:
            # Use CloudFront CDN URLs for caching
            url = get_cloudfront_url(img.s3_key)
            thumbnail_url = get_cloudfront_url(img.s3_key, is_thumbnail=True)
        else:
            # Use API endpoints for local development
            url = f"{base_url}/api/v1/books/{book_id}/images/{img.id}/file"
            thumbnail_url = f"{base_url}/api/v1/books/{book_id}/images/{img.id}/thumbnail"

        result.append(
            {
                "id": img.id,
                "s3_key": img.s3_key,
                "original_filename": img.original_filename,
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
        if settings.is_aws_lambda:
            # Use CloudFront CDN URLs for caching
            url = get_cloudfront_url(image.s3_key)
            thumbnail_url = get_cloudfront_url(image.s3_key, is_thumbnail=True)
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


@router.put("/reorder")
def reorder_images(
    book_id: int,
    image_ids: list[int] = Body(..., embed=False),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Reorder images by providing ordered list of image IDs. Requires editor role."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Verify all image_ids belong to this book
    existing_images = (
        db.query(BookImage).filter(BookImage.book_id == book_id, BookImage.id.in_(image_ids)).all()
    )

    if len(existing_images) != len(image_ids):
        raise HTTPException(
            status_code=400,
            detail="Some image IDs do not belong to this book",
        )

    # Capture old primary before reordering
    old_primary_id = None
    for img in existing_images:
        if img.is_primary:
            old_primary_id = img.id
            break

    # Update display_order based on position in the array
    # Also update is_primary: first image becomes primary, others become non-primary
    for order, image_id in enumerate(image_ids):
        db.query(BookImage).filter(BookImage.id == image_id).update(
            {
                BookImage.display_order: order,
                BookImage.is_primary: (order == 0),  # First image is primary
            }
        )

    db.commit()

    # Trigger image processing if primary changed
    new_primary_id = image_ids[0] if image_ids else None
    if new_primary_id and new_primary_id != old_primary_id:
        try:
            queue_image_processing(db, book_id, new_primary_id)
        except Exception:
            logger.exception("Failed to queue image processing")

    return {"message": "Images reordered successfully", "order": image_ids}


@router.get("/{image_id}/file")
def get_image_file(book_id: int, image_id: int, db: Session = Depends(get_db)):
    """Serve the actual image file or redirect to CloudFront/S3."""
    from fastapi.responses import RedirectResponse

    image = (
        db.query(BookImage).filter(BookImage.id == image_id, BookImage.book_id == book_id).first()
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if settings.is_aws_lambda:
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

    if settings.is_aws_lambda:
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
                generate_thumbnail(original_path, thumbnail_path)  # Ignore result

        # If thumbnail still doesn't exist, fall back to original
        if not thumbnail_path.exists():
            file_path = LOCAL_IMAGES_PATH / image.s3_key
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Image file not found")
            return FileResponse(file_path)

        return FileResponse(thumbnail_path)


@router.post("", status_code=201, response_model=ImageUploadResponse)
async def upload_image(
    book_id: int,
    file: UploadFile = File(...),
    image_type: str = Query(default="detail"),
    is_primary: bool = Query(default=False),
    caption: str = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
) -> ImageUploadResponse:
    """Upload a new image for a book. Requires editor role."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    ensure_images_dir()

    # Read file content and calculate hash for deduplication
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate (same hash already exists for this book)
    existing = (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id, BookImage.content_hash == content_hash)
        .first()
    )
    if existing:
        # Return existing image info instead of uploading duplicate
        base_url = get_api_base_url()
        if settings.is_aws_lambda:
            url = get_cloudfront_url(existing.s3_key)
            thumbnail_url = get_cloudfront_url(existing.s3_key, is_thumbnail=True)
        else:
            url = f"{base_url}/api/v1/books/{book_id}/images/{existing.id}/file"
            thumbnail_url = f"{base_url}/api/v1/books/{book_id}/images/{existing.id}/thumbnail"
        return ImageUploadResponse(
            id=existing.id,
            url=url,
            thumbnail_url=thumbnail_url,
            image_type=existing.image_type,
            is_primary=existing.is_primary,
            thumbnail_status="skipped",
            duplicate=True,
            message="Image already exists (identical content)",
        )

    # Generate unique filename with extension from original file
    ext = Path(file.filename).suffix or ".jpg"
    unique_name = f"{book_id}_{uuid.uuid4().hex}{ext}"

    # Detect format once from magic bytes - reuse for extension fix and S3 content type
    # Need at least MIN_DETECTION_BYTES for detection; use filename extension as fallback
    detected_format = (
        detect_format(content[:MIN_DETECTION_BYTES])
        if len(content) >= MIN_DETECTION_BYTES
        else ImageFormat.UNKNOWN
    )

    # Fix extension based on detected format
    if detected_format != ImageFormat.UNKNOWN:
        base = unique_name.rsplit(".", 1)[0]
        unique_name = base + get_extension(detected_format)

    file_path = LOCAL_IMAGES_PATH / unique_name

    # Save file (write content we already read) - Issue #858: use async I/O
    def write_file():
        with open(file_path, "wb") as buffer:
            buffer.write(content)

    await asyncio.to_thread(write_file)

    # Generate thumbnail - capture result for response (Issue #866)
    # Issue #858: run blocking PIL operations in thread pool
    thumbnail_name = get_thumbnail_key(unique_name)
    thumbnail_path = LOCAL_IMAGES_PATH / thumbnail_name
    thumbnail_success, thumbnail_error = await asyncio.to_thread(
        generate_thumbnail, file_path, thumbnail_path
    )
    if not thumbnail_success:
        logger.warning(f"Thumbnail generation failed for book {book_id}: {thumbnail_error}")

    # Upload to S3 in production - Issue #858: wrap blocking boto3 calls
    if settings.is_aws_lambda:
        s3 = get_s3_client()

        # Get content type from already-detected format (no redundant detection)
        content_type = get_content_type(detected_format)

        s3_key = f"{S3_IMAGES_PREFIX}{unique_name}"
        s3_thumbnail_key = f"{S3_IMAGES_PREFIX}{thumbnail_name}"

        # Upload main image (blocking -> thread pool)
        await asyncio.to_thread(
            s3.upload_file,
            str(file_path),
            settings.images_bucket,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )

        # Upload thumbnail (blocking -> thread pool)
        if thumbnail_path.exists():
            await asyncio.to_thread(
                s3.upload_file,
                str(thumbnail_path),
                settings.images_bucket,
                s3_thumbnail_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

        # Clean up local files (Lambda has limited /tmp space)
        file_path.unlink(missing_ok=True)
        thumbnail_path.unlink(missing_ok=True)

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
        original_filename=file.filename,
        content_hash=content_hash,
        image_type=image_type,
        display_order=max_order,
        is_primary=is_primary,
        caption=caption,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    # Trigger image processing if this is the primary image
    if image.is_primary:
        try:
            queue_image_processing(db, book_id, image.id)
        except Exception:
            logger.exception("Failed to queue image processing")

    return ImageUploadResponse(
        id=image.id,
        url=f"/api/v1/books/{book_id}/images/{image.id}/file",
        thumbnail_url=f"/api/v1/books/{book_id}/images/{image.id}/thumbnail",
        image_type=image.image_type,
        is_primary=image.is_primary,
        thumbnail_status="generated" if thumbnail_success else "failed",
        thumbnail_error=thumbnail_error if not thumbnail_success else None,
    )


@router.put("/{image_id}")
def update_image(
    book_id: int,
    image_id: int,
    image_type: str = Query(default=None),
    is_primary: bool = Query(default=None),
    caption: str = Query(default=None),
    display_order: int = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update image metadata. Requires editor role."""
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
def delete_image(
    book_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Delete an image. Requires editor role."""
    import logging

    logger = logging.getLogger(__name__)
    image = (
        db.query(BookImage).filter(BookImage.id == image_id, BookImage.book_id == book_id).first()
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete file and thumbnail from storage
    if settings.is_aws_lambda:
        # In production, delete from S3
        s3 = get_s3_client()
        for key in [image.s3_key, get_thumbnail_key(image.s3_key)]:
            try:
                s3.delete_object(
                    Bucket=settings.images_bucket,
                    Key=f"{S3_IMAGES_PREFIX}{key}",
                )
            except Exception as e:
                # S3 delete failures are logged but don't fail the operation
                # because the database record is the source of truth.
                # Orphaned S3 objects can be cleaned up by lifecycle rules.
                logger.warning("S3 delete failed for %s: %s (operation continues)", key, e)
    else:
        # In development, delete from local filesystem
        file_path = LOCAL_IMAGES_PATH / image.s3_key
        if file_path.exists():
            file_path.unlink()

        thumbnail_path = LOCAL_IMAGES_PATH / get_thumbnail_key(image.s3_key)
        if thumbnail_path.exists():
            thumbnail_path.unlink()

    # Delete record
    db.delete(image)
    db.commit()


# Bulk register images from S3 keys (for CLI/automation)
@router.post("/register", status_code=201)
def register_images(
    book_id: int,
    images: list[dict] = Body(...),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Register images already uploaded to S3. Requires editor role.

    Body should be a list of objects with:
    - s3_key: str (required)
    - image_type: str (optional, default "detail")
    - display_order: int (optional, auto-incremented)
    - is_primary: bool (optional, default False)
    - caption: str (optional)
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get current max display order
    current_max = db.query(BookImage).filter(BookImage.book_id == book_id).count()

    created = []
    for i, img_data in enumerate(images):
        s3_key = img_data.get("s3_key")
        if not s3_key:
            raise HTTPException(status_code=400, detail=f"Image {i} missing s3_key")

        image = BookImage(
            book_id=book_id,
            s3_key=s3_key,
            image_type=img_data.get("image_type", "detail"),
            display_order=img_data.get("display_order", current_max + i),
            is_primary=img_data.get("is_primary", False),
            caption=img_data.get("caption"),
        )
        db.add(image)
        created.append(s3_key)

    db.commit()
    return {"message": f"Registered {len(created)} images", "s3_keys": created}


@router.post("/regenerate-thumbnails")
def regenerate_thumbnails(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Regenerate thumbnails for all images of a book. Requires editor role.

    Downloads each original image from S3, generates a thumbnail, and uploads it.
    """
    if not settings.is_aws_lambda:
        raise HTTPException(
            status_code=400, detail="Thumbnail regeneration only available in production"
        )

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    images = db.query(BookImage).filter(BookImage.book_id == book_id).all()
    if not images:
        return {"message": "No images to process", "regenerated": 0}

    s3 = get_s3_client()
    regenerated = []
    errors = []

    for img in images:
        try:
            # Download original from S3
            s3_key = f"{S3_IMAGES_PREFIX}{img.s3_key}"
            local_path = LOCAL_IMAGES_PATH / img.s3_key
            local_path.parent.mkdir(parents=True, exist_ok=True)

            s3.download_file(settings.images_bucket, s3_key, str(local_path))

            # Generate thumbnail
            thumbnail_name = get_thumbnail_key(img.s3_key)
            thumbnail_path = LOCAL_IMAGES_PATH / thumbnail_name

            success, error_msg = generate_thumbnail(local_path, thumbnail_path)
            if success:
                # Upload thumbnail to S3
                s3_thumbnail_key = f"{S3_IMAGES_PREFIX}{thumbnail_name}"
                s3.upload_file(
                    str(thumbnail_path),
                    settings.images_bucket,
                    s3_thumbnail_key,
                    ExtraArgs={"ContentType": "image/jpeg"},
                )
                regenerated.append(img.s3_key)

                # Clean up local files
                if local_path.exists():
                    local_path.unlink()
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
            else:
                errors.append(f"{img.s3_key}: {error_msg}")
        except Exception as e:
            errors.append(f"{img.s3_key}: {e!s}")

    result = {
        "message": f"Regenerated {len(regenerated)} thumbnails",
        "regenerated": len(regenerated),
        "s3_keys": regenerated,
    }
    if errors:
        result["errors"] = errors

    return result


# Standalone placeholder endpoint (not book-specific)
@router.get("/placeholder", include_in_schema=False)
def get_placeholder_image():
    """Serve placeholder image for books without images."""
    if PLACEHOLDER_PATH.exists():
        return FileResponse(PLACEHOLDER_PATH)

    # Return a simple 1x1 gray pixel if no placeholder exists
    raise HTTPException(status_code=404, detail="Placeholder not configured")
