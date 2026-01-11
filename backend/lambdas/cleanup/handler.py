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


def cleanup_orphaned_images(
    db: Session,
    bucket: str,
    delete: bool = False,
) -> dict:
    """Find and optionally delete orphaned images in S3.

    Uses pagination to handle buckets with more than 1000 objects.
    Only checks images under the 'books/' prefix to avoid deleting
    other bucket contents (lambda packages, listings, etc.).

    Args:
        db: Database session
        bucket: S3 bucket name
        delete: If True, delete orphaned images. Otherwise dry run.

    Returns:
        Dict with:
        - total_count: number of orphans
        - total_bytes: total size of all orphans
        - orphans_by_book: list of groups with folder_id, book_id, book_title, count, bytes, keys
        - deleted: number deleted (0 if delete=False)
        - found/orphans_found: legacy fields for backwards compatibility
    """
    s3 = boto3.client("s3")

    # S3 prefix for book images - MUST match what's used in image upload
    S3_BOOKS_PREFIX = "books/"

    # Use paginator to handle > 1000 objects
    # IMPORTANT: Only list objects under books/ prefix
    paginator = s3.get_paginator("list_objects_v2")
    s3_keys_full = set()  # Full S3 keys with prefix (for deletion)
    s3_keys_stripped = set()  # Keys without prefix (for comparison with DB)
    # Track size per key for byte calculations
    s3_key_sizes: dict[str, int] = {}

    for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
        for obj in page.get("Contents", []):
            full_key = obj["Key"]
            size = obj.get("Size", 0)
            s3_keys_full.add(full_key)
            s3_key_sizes[full_key] = size
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
    # BUT: flat-format thumbnails (thumb_{id}_{uuid}.ext) are NOT stored in DB
    # They're derived from main images, so check if main image exists
    orphaned_stripped = set()
    for stripped_key in s3_keys_stripped:
        if stripped_key in db_keys:
            continue  # Direct match in DB - not orphan

        # Check if this is a flat-format thumbnail (thumb_{id}_{uuid}.ext)
        # If so, check if the main image (without thumb_ prefix) exists in DB
        if stripped_key.startswith("thumb_"):
            main_key = stripped_key[6:]  # Remove "thumb_" prefix
            if main_key in db_keys:
                continue  # Main image exists in DB - thumbnail is valid, not orphan

        orphaned_stripped.add(stripped_key)

    # Convert back to full S3 keys for deletion
    orphaned_full_keys = {f"{S3_BOOKS_PREFIX}{k}" for k in orphaned_stripped}

    # Calculate total bytes for all orphans
    total_bytes = sum(s3_key_sizes.get(key, 0) for key in orphaned_full_keys)

    # Group orphans by book ID extracted from S3 key
    # Three formats exist:
    #   1. Nested (scraper):     books/{book_id}/image.webp       -> parts[1] = "500"
    #   2. Nested thumb:         books/thumb_{book_id}/image.webp -> parts[1] = "thumb_500"
    #   3. Flat (uploads):       books/{book_id}_{uuid}.ext       -> parts[1] = "10_abc.jpg"
    orphans_by_folder: dict[int, list[tuple[str, int]]] = {}
    for key in orphaned_full_keys:
        parts = key.split("/")
        if len(parts) >= 2:
            folder_part = parts[1]

            # Strip thumb_ prefix if present (nested thumbnail directories)
            if folder_part.startswith("thumb_"):
                folder_part = folder_part[6:]  # Remove "thumb_" prefix

            try:
                # Try nested format first (folder_part is just the book_id)
                folder_id = int(folder_part)
            except ValueError:
                # Try flat format: extract book_id before underscore
                try:
                    folder_id = int(folder_part.split("_")[0])
                except (ValueError, IndexError):
                    # Neither format matches, skip this key
                    continue

            size = s3_key_sizes.get(key, 0)
            if folder_id not in orphans_by_folder:
                orphans_by_folder[folder_id] = []
            orphans_by_folder[folder_id].append((key, size))

    # Resolve book IDs to titles
    folder_ids = list(orphans_by_folder.keys())
    book_titles: dict[int, str | None] = {}
    book_exists: dict[int, bool] = {}
    if folder_ids:
        books = db.query(Book.id, Book.title).filter(Book.id.in_(folder_ids)).all()
        for book_id, title in books:
            book_titles[book_id] = title
            book_exists[book_id] = True

    # Build orphans_by_book list with size info
    orphans_by_book = []
    for folder_id in sorted(orphans_by_folder.keys()):
        items = orphans_by_folder[folder_id]
        folder_bytes = sum(size for _, size in items)
        folder_keys = [key for key, _ in items]

        orphans_by_book.append(
            {
                "folder_id": folder_id,
                "book_id": folder_id if book_exists.get(folder_id) else None,
                "book_title": book_titles.get(folder_id),
                "count": len(items),
                "bytes": folder_bytes,
                "keys": folder_keys[:10],  # Cap keys to prevent huge response
            }
        )

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
        "total_bytes": total_bytes,
        "orphans_by_book": orphans_by_book,
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


def cleanup_orphaned_images_with_progress(
    bucket: str,
    job_id: str,
    progress_update_interval: int = 500,
) -> dict:
    """Delete orphans with progress updates to DB.

    This function is invoked asynchronously by Lambda to perform batch
    deletion of orphaned images while updating progress in the database.

    Designed to avoid Lambda timeout with proper DB connection management:
    - Phase 1: S3 scan (no DB connection held)
    - Phase 2: Quick DB query for referenced keys
    - Phase 3: Calculate orphans (no DB)
    - Phase 4: Update job with fresh totals and set status to running
    - Phase 5: Delete in batches using delete_objects API, update progress
    - Phase 6: Final status update

    Args:
        bucket: S3 bucket name containing images
        job_id: UUID of the CleanupJob to track progress
        progress_update_interval: Update progress every N items deleted

    Returns:
        Dict with deleted count, bytes_freed, and failed_count
    """
    from app.models.cleanup_job import CleanupJob

    s3 = boto3.client("s3")
    S3_BOOKS_PREFIX = "books/"
    S3_DELETE_BATCH_SIZE = 1000  # Max keys per delete_objects call

    # Track results
    deleted_count = 0
    deleted_bytes = 0
    failed_count = 0
    error_message = None

    try:
        # Phase 1: S3 scan (no DB connection)
        paginator = s3.get_paginator("list_objects_v2")
        s3_keys_stripped = set()
        s3_key_sizes: dict[str, int] = {}

        for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
            for obj in page.get("Contents", []):
                full_key = obj["Key"]
                size = obj.get("Size", 0)
                s3_key_sizes[full_key] = size
                if full_key.startswith(S3_BOOKS_PREFIX):
                    stripped_key = full_key[len(S3_BOOKS_PREFIX) :]
                    s3_keys_stripped.add(stripped_key)

        # Phase 2: Quick DB query for referenced keys (acquire, query, release)
        db = SessionLocal()
        try:
            db_keys = {key for (key,) in db.query(BookImage.s3_key).all() if key}
        finally:
            db.close()

        # Phase 3: Calculate orphans (no DB)
        # BUT: flat-format thumbnails (thumb_{id}_{uuid}.ext) are NOT stored in DB
        # They're derived from main images, so check if main image exists
        orphaned_stripped = set()
        for stripped_key in s3_keys_stripped:
            if stripped_key in db_keys:
                continue  # Direct match in DB - not orphan

            # Check if this is a flat-format thumbnail (thumb_{id}_{uuid}.ext)
            # If so, check if the main image (without thumb_ prefix) exists in DB
            if stripped_key.startswith("thumb_"):
                main_key = stripped_key[6:]  # Remove "thumb_" prefix
                if main_key in db_keys:
                    continue  # Main image exists in DB - thumbnail is valid, not orphan

            orphaned_stripped.add(stripped_key)

        orphaned_full_keys = [f"{S3_BOOKS_PREFIX}{k}" for k in orphaned_stripped]

        # Calculate fresh totals from scan
        total_count = len(orphaned_full_keys)
        total_bytes = sum(s3_key_sizes.get(key, 0) for key in orphaned_full_keys)

        # Phase 4: Update job with fresh totals and set status to running
        db = SessionLocal()
        try:
            job = db.get(CleanupJob, job_id)
            if not job:
                return {"error": f"Job {job_id} not found"}

            # Fix 1: Update totals from fresh scan (not stale frontend values)
            job.total_count = total_count
            job.total_bytes = total_bytes
            job.status = "running"
            db.commit()
        finally:
            db.close()

        # Phase 5: Delete in batches using delete_objects API
        # Build list of (key, size) for tracking bytes
        orphan_items = [(key, s3_key_sizes.get(key, 0)) for key in orphaned_full_keys]

        # Process in batches of S3_DELETE_BATCH_SIZE (1000 max for delete_objects)
        for batch_start in range(0, len(orphan_items), S3_DELETE_BATCH_SIZE):
            batch_end = min(batch_start + S3_DELETE_BATCH_SIZE, len(orphan_items))
            batch = orphan_items[batch_start:batch_end]

            # Build delete request
            delete_keys = [{"Key": key} for key, _ in batch]

            # Call delete_objects API (up to 1000 keys per call)
            response = s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": delete_keys, "Quiet": False},
            )

            # Track successful deletes
            deleted_list = response.get("Deleted", [])
            deleted_keys_set = {d["Key"] for d in deleted_list}
            for key, size in batch:
                if key in deleted_keys_set:
                    deleted_count += 1
                    deleted_bytes += size

            # Track failed deletes (Fix 7)
            errors_list = response.get("Errors", [])
            failed_count += len(errors_list)

            # Update progress after each batch (acquire, update, release)
            if deleted_count >= progress_update_interval or batch_end == len(orphan_items):
                db = SessionLocal()
                try:
                    job = db.get(CleanupJob, job_id)
                    if job:
                        job.deleted_count = deleted_count
                        job.deleted_bytes = deleted_bytes
                        db.commit()
                finally:
                    db.close()

        # Build error message if there were partial failures
        if failed_count > 0:
            error_message = f"{failed_count} objects failed to delete"

        # Phase 6: Final status update (acquire, update, release)
        db = SessionLocal()
        try:
            job = db.get(CleanupJob, job_id)
            if job:
                job.deleted_count = deleted_count
                job.deleted_bytes = deleted_bytes
                job.failed_count = failed_count
                job.status = "completed"  # Completed even with partial failures
                job.completed_at = datetime.now(UTC)
                if error_message:
                    job.error_message = error_message
                db.commit()
        finally:
            db.close()

        return {
            "deleted": deleted_count,
            "bytes_freed": deleted_bytes,
            "failed_count": failed_count,
        }
    except Exception as e:
        # Update job with failure status (for exceptions, not partial failures)
        try:
            db = SessionLocal()
            try:
                job = db.get(CleanupJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.deleted_count = deleted_count
                    job.deleted_bytes = deleted_bytes
                    job.failed_count = failed_count
                    db.commit()
            finally:
                db.close()
        except Exception:  # noqa: S110 - Don't mask original error
            pass
        return {"error": str(e)}


def cleanup_stale_listings(
    bucket: str,
    age_days: int = 30,
    delete: bool = False,
) -> dict:
    """Find and optionally delete stale listing images.

    Scans the listings/ S3 prefix and identifies objects older than
    the specified age threshold. No database interaction needed.

    Args:
        bucket: S3 bucket name
        age_days: Delete objects older than this many days (default 30)
        delete: If True, delete stale objects. Otherwise dry run.

    Returns:
        Dict with:
        - total_count: number of stale objects
        - total_bytes: total size of stale objects
        - age_threshold_days: the threshold used
        - listings_by_item: list of groups with item_id, count, bytes, oldest
        - deleted_count: number deleted (0 if delete=False)
    """
    s3 = boto3.client("s3")
    S3_LISTINGS_PREFIX = "listings/"
    S3_DELETE_BATCH_SIZE = 1000

    cutoff_date = datetime.now(UTC) - timedelta(days=age_days)

    # Scan listings/ prefix
    paginator = s3.get_paginator("list_objects_v2")
    stale_keys: list[tuple[str, int, datetime]] = []  # (key, size, last_modified)

    for page in paginator.paginate(Bucket=bucket, Prefix=S3_LISTINGS_PREFIX):
        for obj in page.get("Contents", []):
            last_modified = obj["LastModified"]
            # Ensure timezone-aware comparison
            if last_modified.tzinfo is None:
                last_modified = last_modified.replace(tzinfo=UTC)

            if last_modified < cutoff_date:
                stale_keys.append((obj["Key"], obj.get("Size", 0), last_modified))

    # Group by item_id
    items_map: dict[str, list[tuple[str, int, datetime]]] = {}
    for key, size, last_modified in stale_keys:
        # Extract item_id from path: listings/{item_id}/filename
        parts = key.split("/")
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id not in items_map:
                items_map[item_id] = []
            items_map[item_id].append((key, size, last_modified))

    # Build listings_by_item response
    listings_by_item = []
    for item_id in sorted(items_map.keys()):
        items = items_map[item_id]
        item_bytes = sum(size for _, size, _ in items)
        oldest = min(lm for _, _, lm in items)
        listings_by_item.append(
            {
                "item_id": item_id,
                "count": len(items),
                "bytes": item_bytes,
                "oldest": oldest.isoformat(),
            }
        )

    total_count = len(stale_keys)
    total_bytes = sum(size for _, size, _ in stale_keys)

    # Delete if requested
    deleted_count = 0
    if delete and stale_keys:
        all_keys = [key for key, _, _ in stale_keys]

        # Batch delete (max 1000 per call)
        for i in range(0, len(all_keys), S3_DELETE_BATCH_SIZE):
            batch = all_keys[i : i + S3_DELETE_BATCH_SIZE]
            delete_request = {"Objects": [{"Key": k} for k in batch], "Quiet": False}
            response = s3.delete_objects(Bucket=bucket, Delete=delete_request)
            deleted_count += len(response.get("Deleted", []))

    return {
        "total_count": total_count,
        "total_bytes": total_bytes,
        "age_threshold_days": age_days,
        "listings_by_item": listings_by_item,
        "deleted_count": deleted_count,
    }


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
            # Pass through detailed scan results for /cleanup/orphans/scan endpoint
            result["total_bytes"] = orphan_result.get("total_bytes", 0)
            result["orphans_by_book"] = orphan_result.get("orphans_by_book", [])

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

    Event payload for standard cleanup:
        action: "all" | "stale" | "expired" | "orphans" | "archives"
        bucket: S3 bucket name (required for orphans action)
        delete_orphans: bool (default False)

    Event payload for background deletion with progress:
        job_id: UUID of CleanupJob to track progress
        bucket: S3 bucket name

    Args:
        event: Lambda event dict
        context: Lambda context (unused)

    Returns:
        Dict with cleanup results
    """
    # Check for job_id - indicates background deletion with progress tracking
    if event.get("job_id"):
        return cleanup_orphaned_images_with_progress(
            bucket=event["bucket"],
            job_id=event["job_id"],
        )

    # Standard cleanup action
    return asyncio.run(_async_handler(event))
