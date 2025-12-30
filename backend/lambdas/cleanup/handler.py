"""Cleanup Lambda handler for stale data maintenance."""

import asyncio
from datetime import UTC, datetime, timedelta

import boto3
import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Book
from app.models.image import BookImage
from app.services.archive import archive_url

# Batch size limits to prevent Lambda timeout (300s max)
EXPIRED_CHECK_BATCH_SIZE = 25  # 10s timeout × 25 = ~250s max
ARCHIVE_RETRY_BATCH_SIZE = 10  # Archive calls can be slow


def cleanup_stale_evaluations(db: Session) -> int:
    """Archive books stuck in EVALUATING status for > 30 days.

    Args:
        db: Database session

    Returns:
        Count of books archived
    """
    stale_threshold = datetime.now(UTC) - timedelta(days=30)

    stale_books = (
        db.query(Book)
        .filter(Book.status == "EVALUATING")
        .filter(Book.updated_at < stale_threshold)
        .all()
    )

    count = 0
    for book in stale_books:
        book.status = "REMOVED"
        count += 1

    db.commit()
    return count


def check_expired_sources(db: Session) -> tuple[int, int]:
    """Check source URLs for books and mark expired ones.

    Only checks a batch per invocation to avoid Lambda timeout.
    Transient network errors leave source_expired as None for retry.

    Args:
        db: Database session

    Returns:
        Tuple of (checked_count, expired_count)
    """
    # Query books with source_url that haven't been checked (batch limited)
    books = (
        db.query(Book)
        .filter(Book.source_url.isnot(None))
        .filter(Book.source_expired.is_(None))
        .limit(EXPIRED_CHECK_BATCH_SIZE)
        .all()
    )

    checked = 0
    expired = 0

    for book in books:
        checked += 1
        try:
            response = httpx.head(book.source_url, timeout=10.0, follow_redirects=True)
            if response.status_code in (404, 410):
                book.source_expired = True
                expired += 1
            else:
                book.source_expired = False
        except httpx.TimeoutException:
            # Transient timeout - leave as None to retry later
            pass
        except httpx.ConnectError:
            # Transient connection error - leave as None to retry later
            pass
        except httpx.HTTPError as e:
            # Check if it's a definitive HTTP error in the exception
            error_str = str(e).lower()
            if "404" in error_str or "410" in error_str or "not found" in error_str:
                book.source_expired = True
                expired += 1
            # else leave as None to retry later

    db.commit()
    return checked, expired


def cleanup_orphaned_images(db: Session, bucket: str, delete: bool = False) -> dict:
    """Find and optionally delete orphaned images in S3.

    Uses pagination to handle buckets with more than 1000 objects.
    Only checks images under the 'books/' prefix to avoid deleting
    other bucket contents (lambda packages, listings, etc.).

    Args:
        db: Database session
        bucket: S3 bucket name
        delete: If True, delete orphaned images. Otherwise dry run.

    Returns:
        Dict with found, deleted counts and list of orphaned keys
    """
    s3 = boto3.client("s3")

    # S3 prefix for book images - MUST match what's used in image upload
    S3_BOOKS_PREFIX = "books/"

    # Use paginator to handle > 1000 objects
    # IMPORTANT: Only list objects under books/ prefix
    paginator = s3.get_paginator("list_objects_v2")
    s3_keys_full = set()  # Full S3 keys with prefix (for deletion)
    s3_keys_stripped = set()  # Keys without prefix (for comparison with DB)

    for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
        for obj in page.get("Contents", []):
            full_key = obj["Key"]
            s3_keys_full.add(full_key)
            # Strip the books/ prefix to match DB storage format
            # DB stores: "515/image_00.webp"
            # S3 stores: "books/515/image_00.webp"
            if full_key.startswith(S3_BOOKS_PREFIX):
                stripped_key = full_key[len(S3_BOOKS_PREFIX) :]
                s3_keys_stripped.add(stripped_key)

    # Get all image keys from database (stored WITHOUT books/ prefix)
    db_keys = {key for (key,) in db.query(BookImage.s3_key).all() if key}

    # Find orphaned keys (in S3 but not in DB)
    # Compare using stripped keys (without prefix)
    orphaned_stripped = s3_keys_stripped - db_keys

    # Convert back to full S3 keys for deletion
    orphaned_full_keys = {f"{S3_BOOKS_PREFIX}{k}" for k in orphaned_stripped}

    deleted = 0
    if delete:
        for key in orphaned_full_keys:
            s3.delete_object(Bucket=bucket, Key=key)
            deleted += 1

    # Calculate orphan percentage for sanity check
    orphan_percentage = (
        round(len(orphaned_full_keys) / len(s3_keys_full) * 100, 1) if s3_keys_full else 0
    )

    # Group orphans by top-level prefix for visibility
    # This helps catch bugs like "why are there orphans outside books/?"
    orphans_by_prefix: dict[str, int] = {}
    for key in orphaned_full_keys:
        prefix = key.split("/")[0] + "/" if "/" in key else "(root)"
        orphans_by_prefix[prefix] = orphans_by_prefix.get(prefix, 0) + 1

    # Build contextual response for dry run review
    result = {
        "scan_prefix": S3_BOOKS_PREFIX,
        "total_objects_scanned": len(s3_keys_full),
        "objects_in_database": len(db_keys),
        "orphans_found": len(orphaned_full_keys),
        "orphans_by_prefix": orphans_by_prefix,
        "orphan_percentage": orphan_percentage,
        "sample_orphan_keys": list(orphaned_full_keys)[:10],
        "deleted": deleted,
    }

    # Add warning if high orphan rate (indicates likely bug)
    if orphan_percentage > 50:
        result["WARNING"] = f"High orphan rate ({orphan_percentage}%) - verify before deleting"

    # Legacy field for backward compatibility (capped to prevent huge responses)
    result["found"] = result["orphans_found"]
    result["keys"] = list(orphaned_full_keys)[:100]

    return result


async def retry_failed_archives(db: Session) -> dict:
    """Retry archiving for books with failed archive status.

    Only retries books with less than 3 attempts.
    Batch limited to prevent Lambda timeout.

    Args:
        db: Database session

    Returns:
        Dict with retried, succeeded, failed counts
    """
    MAX_ATTEMPTS = 3

    # Query books with failed archive status and < max attempts (batch limited)
    books = (
        db.query(Book)
        .filter(Book.archive_status == "failed")
        .filter(Book.archive_attempts < MAX_ATTEMPTS)
        .limit(ARCHIVE_RETRY_BATCH_SIZE)
        .all()
    )

    retried = 0
    succeeded = 0
    failed = 0

    for book in books:
        if not book.source_url:
            continue

        retried += 1
        book.archive_attempts += 1

        result = await archive_url(book.source_url)

        if result["status"] == "success":
            book.archive_status = "success"
            book.source_archived_url = result["archived_url"]
            succeeded += 1
        else:
            failed += 1

    db.commit()
    return {
        "retried": retried,
        "succeeded": succeeded,
        "failed": failed,
    }


async def _async_handler(event: dict) -> dict:
    """Async implementation of cleanup handler.

    Args:
        event: Lambda event dict

    Returns:
        Dict with cleanup results
    """
    action = event.get("action", "all")
    bucket = event.get("bucket")
    delete_orphans = event.get("delete_orphans", False)

    valid_actions = {"all", "stale", "expired", "orphans", "archives"}
    if action not in valid_actions:
        return {"error": f"Unknown action: {action}. Valid actions: {valid_actions}"}

    if action in ("orphans", "all") and not bucket:
        return {"error": "bucket is required for orphans action"}

    result = {}

    # Create database session directly (not via generator)
    db = SessionLocal()

    try:
        if action in ("all", "stale"):
            count = cleanup_stale_evaluations(db)
            result["stale_evaluations_archived"] = count

        if action in ("all", "expired"):
            checked, expired = check_expired_sources(db)
            result["sources_checked"] = checked
            result["sources_expired"] = expired

        if action in ("all", "orphans"):
            orphan_result = cleanup_orphaned_images(db, bucket=bucket, delete=delete_orphans)
            result["orphans_found"] = orphan_result["found"]
            result["orphans_deleted"] = orphan_result["deleted"]

        if action in ("all", "archives"):
            archive_result = await retry_failed_archives(db)
            result["archives_retried"] = archive_result["retried"]
            result["archives_succeeded"] = archive_result["succeeded"]
            result["archives_failed"] = archive_result["failed"]

    finally:
        db.close()

    return result


def handler(event: dict, context) -> dict:
    """Cleanup Lambda handler.

    Event payload:
        action: "all" | "stale" | "expired" | "orphans" | "archives"
        bucket: S3 bucket name (required for orphans action)
        delete_orphans: bool (default False)

    Args:
        event: Lambda event dict
        context: Lambda context (unused)

    Returns:
        Dict with cleanup results
    """
    return asyncio.run(_async_handler(event))
