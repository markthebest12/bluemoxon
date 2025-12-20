"""Image cleanup service for removing unrelated images."""

import logging

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import BookImage

logger = logging.getLogger(__name__)

settings = get_settings()

# S3 prefix for book images (duplicated from images.py to avoid circular import)
S3_IMAGES_PREFIX = "books/"


def get_thumbnail_key(s3_key: str) -> str:
    """Get the S3 key for a thumbnail from the original image key.

    Example: 'book_123_abc.jpg' -> 'thumb_book_123_abc.jpg'
    """
    return f"thumb_{s3_key}"


def delete_unrelated_images(
    book_id: int,
    unrelated_indices: list[int],
    unrelated_reasons: dict[str, str],
    db: Session,
) -> dict:
    """Delete images identified as unrelated to the book.

    Args:
        book_id: ID of the book
        unrelated_indices: List of 0-based image indices to delete
        unrelated_reasons: Dict mapping index to reason for deletion
        db: Database session

    Returns:
        Dict with deletion results:
            - deleted_count: Number of images deleted
            - deleted_keys: List of S3 keys deleted
            - errors: List of any errors encountered
    """
    if not unrelated_indices:
        return {"deleted_count": 0, "deleted_keys": [], "errors": []}

    logger.info(
        f"Deleting {len(unrelated_indices)} unrelated images from book {book_id}: "
        f"indices {unrelated_indices}"
    )

    # Get images for this book, ordered by display_order
    images = (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id)
        .order_by(BookImage.display_order)
        .all()
    )

    if not images:
        logger.warning(f"No images found for book {book_id}")
        return {"deleted_count": 0, "deleted_keys": [], "errors": ["No images found"]}

    deleted_keys = []
    errors = []

    # Initialize S3 client
    s3 = boto3.client("s3")
    bucket = settings.images_bucket

    for idx in unrelated_indices:
        if idx < 0 or idx >= len(images):
            logger.warning(
                f"Invalid image index {idx} for book {book_id} (has {len(images)} images)"
            )
            errors.append(f"Invalid index {idx}")
            continue

        image = images[idx]
        reason = unrelated_reasons.get(str(idx), "AI identified as unrelated")

        logger.info(f"Deleting image {image.id} (index {idx}) from book {book_id}: {reason}")

        # Delete from S3 (both image and thumbnail)
        if image.s3_key:
            # Database stores s3_key without prefix (e.g., "515/image_00.webp")
            # S3 stores with prefix (e.g., "books/515/image_00.webp")
            full_s3_key = f"{S3_IMAGES_PREFIX}{image.s3_key}"
            thumbnail_key = f"{S3_IMAGES_PREFIX}{get_thumbnail_key(image.s3_key)}"

            try:
                # Delete the main image
                s3.delete_object(Bucket=bucket, Key=full_s3_key)
                logger.info(f"Deleted S3 object: {full_s3_key}")

                # Delete the thumbnail (best effort, don't fail if missing)
                try:
                    s3.delete_object(Bucket=bucket, Key=thumbnail_key)
                    logger.info(f"Deleted S3 thumbnail: {thumbnail_key}")
                except ClientError as thumb_err:
                    logger.warning(f"Failed to delete thumbnail {thumbnail_key}: {thumb_err}")

                deleted_keys.append(full_s3_key)
            except ClientError as e:
                error_msg = f"Failed to delete S3 object {full_s3_key}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue  # Don't delete DB record if S3 delete failed

        # Delete from database
        db.delete(image)

    # Commit deletions
    db.commit()

    # Reorder remaining images
    remaining_images = (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id)
        .order_by(BookImage.display_order)
        .all()
    )
    for new_order, img in enumerate(remaining_images):
        if img.display_order != new_order:
            img.display_order = new_order
    db.commit()

    logger.info(
        f"Deleted {len(deleted_keys)} unrelated images from book {book_id}, {len(errors)} errors"
    )

    return {
        "deleted_count": len(deleted_keys),
        "deleted_keys": deleted_keys,
        "errors": errors,
    }
