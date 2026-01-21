"""Image migration service for fixing ContentType mismatches.

Supports checkpoint/resume pattern to handle Lambda timeouts on large datasets.
Each migration function accepts a continuation_token and batch_size, returning
the next continuation token (or None if complete) along with stats.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError

from app.utils.image_utils import (
    MIN_DETECTION_BYTES,
    ImageFormat,
    detect_format,
    get_content_type,
)

logger = logging.getLogger(__name__)

S3_IMAGES_PREFIX = "books/"

# Default batch size - processes this many objects before returning
DEFAULT_BATCH_SIZE = 500


@dataclass
class MigrationResult:
    """Result from a migration batch, including continuation state."""

    stats: dict[str, int]
    continuation_token: str | None
    has_more: bool


def _check_bucket_versioning(s3: Any, bucket: str) -> bool:
    """Check if bucket has versioning enabled.

    Returns:
        True if versioning is Enabled, False otherwise (including Suspended).
    """
    try:
        response = s3.get_bucket_versioning(Bucket=bucket)
        status = response.get("Status", "")
        return status == "Enabled"
    except ClientError as e:
        logger.warning(f"Could not check bucket versioning: {e}")
        return False


def _delete_all_versions(
    s3: Any,
    bucket: str,
    key: str,
    errors: list[dict],
) -> int:
    """Delete all versions of an object in a versioned bucket.

    Args:
        s3: S3 client
        bucket: Bucket name
        key: Object key to delete all versions of
        errors: Error list to append to

    Returns:
        Number of versions successfully deleted
    """
    deleted_count = 0

    try:
        # List all versions of this specific object
        paginator = s3.get_paginator("list_object_versions")
        version_objects: list[dict[str, str]] = []

        for page in paginator.paginate(Bucket=bucket, Prefix=key):
            # Get versions
            for version in page.get("Versions", []):
                if version["Key"] == key:
                    version_objects.append({"Key": key, "VersionId": version["VersionId"]})

            # Get delete markers too
            for marker in page.get("DeleteMarkers", []):
                if marker["Key"] == key:
                    version_objects.append({"Key": key, "VersionId": marker["VersionId"]})

        if not version_objects:
            return 0

        # Delete in batches of 1000 (S3 limit)
        for i in range(0, len(version_objects), 1000):
            batch = version_objects[i : i + 1000]
            response = s3.delete_objects(Bucket=bucket, Delete={"Objects": batch})

            # Count successes
            deleted_count += len(batch) - len(response.get("Errors", []))

            # Log any errors
            for error in response.get("Errors", []):
                version_id = error.get("VersionId", "unknown")
                code = error.get("Code", "Unknown")
                message = error.get("Message", "No message")
                errors.append(
                    {
                        "key": f"{key}?versionId={version_id}",
                        "error": f"Delete version failed: {code} - {message}",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                logger.error(f"Failed to delete {key} version {version_id}: {code} - {message}")

        logger.debug(f"Deleted {deleted_count} versions of {key}")

    except ClientError as e:
        errors.append(
            {
                "key": key,
                "error": f"Failed to list/delete versions: {e}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        logger.error(f"Failed to delete versions of {key}: {e}")

    return deleted_count


def _batch_delete_with_errors(
    s3: Any,
    bucket: str,
    objects: list[dict[str, str]],
    errors: list[dict],
    stats: dict[str, int],
) -> None:
    """Delete objects and count actual successes/errors from S3 response.

    Args:
        s3: S3 client
        bucket: Bucket name
        objects: List of {"Key": ...} dicts
        errors: Error list to append to
        stats: Stats dict with "deleted" and "errors" keys to update
    """
    if not objects:
        return

    response = s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})

    # Count actual successful deletions from response
    deleted_objects = response.get("Deleted", [])
    stats["deleted"] += len(deleted_objects)

    # Record per-object errors from response
    for error in response.get("Errors", []):
        key = error.get("Key", "unknown")
        code = error.get("Code", "Unknown")
        message = error.get("Message", "No message")
        errors.append(
            {
                "key": key,
                "error": f"Delete failed: {code} - {message}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        stats["errors"] += 1
        logger.error(f"Failed to delete {key}: {code} - {message}")


def migrate_stage_1(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
    continuation_token: str | None = None,
) -> MigrationResult:
    """Fix ContentType on main images (skip thumbnails).

    Uses S3 range requests to download only first 12 bytes for format detection.
    Processes up to batch_size objects before returning with a continuation token.

    Args:
        s3: Boto3 S3 client
        bucket: S3 bucket name
        dry_run: If True, don't make changes
        limit: Maximum total objects to process (for testing)
        errors: List to append error dicts to
        batch_size: Objects to process before returning (default 500)
        continuation_token: Token from previous call to resume

    Returns:
        MigrationResult with stats and continuation token (None if complete)
    """
    stats = {
        "processed": 0,
        "fixed": 0,
        "already_correct": 0,
        "skipped": 0,
        "errors": 0,
    }
    current_token = continuation_token

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": S3_IMAGES_PREFIX,
            "MaxKeys": 1000,
        }
        if current_token:
            kwargs["ContinuationToken"] = current_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]

            # Skip thumbnails - handled in Stage 2
            if "/thumb_" in key:
                stats["skipped"] += 1
                continue

            # Check limit (total objects across all batches)
            if limit and stats["processed"] >= limit:
                return MigrationResult(
                    stats=stats,
                    continuation_token=None,
                    has_more=False,
                )

            # Check batch size - return early with continuation token
            if stats["processed"] >= batch_size:
                # Return the current S3 token to resume from
                next_token = (
                    response.get("NextContinuationToken") if response.get("IsTruncated") else None
                )
                return MigrationResult(
                    stats=stats,
                    continuation_token=current_token or next_token,
                    has_more=True,
                )

            try:
                # Range request - only first 12 bytes
                range_resp = s3.get_object(Bucket=bucket, Key=key, Range="bytes=0-11")
                magic_bytes = range_resp["Body"].read()

                # Handle truncated/corrupt images with insufficient bytes
                if len(magic_bytes) < MIN_DETECTION_BYTES:
                    logger.warning(
                        f"Skipping {key}: truncated or corrupt "
                        f"(only {len(magic_bytes)} bytes, need {MIN_DETECTION_BYTES})"
                    )
                    stats["skipped"] += 1
                    stats["processed"] += 1
                    continue

                actual_format = detect_format(magic_bytes, strict=False)
                if actual_format == ImageFormat.UNKNOWN:
                    stats["skipped"] += 1
                    stats["processed"] += 1
                    continue

                # Check current metadata
                head = s3.head_object(Bucket=bucket, Key=key)
                current_ct = head.get("ContentType", "")
                expected_ct = get_content_type(actual_format)

                if current_ct != expected_ct:
                    if not dry_run:
                        s3.copy_object(
                            Bucket=bucket,
                            CopySource={"Bucket": bucket, "Key": key},
                            Key=key,
                            MetadataDirective="REPLACE",
                            ContentType=expected_ct,
                        )
                    stats["fixed"] += 1
                    logger.info(
                        f"{'[DRY RUN] ' if dry_run else ''}Fixed {key}: "
                        f"{current_ct} -> {expected_ct}"
                    )
                else:
                    stats["already_correct"] += 1

            except ClientError as e:
                errors.append(
                    {
                        "key": key,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                stats["errors"] += 1
            except Exception as e:
                errors.append(
                    {
                        "key": key,
                        "error": f"Unexpected: {e}",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                stats["errors"] += 1

            stats["processed"] += 1

        if not response.get("IsTruncated"):
            break
        current_token = response["NextContinuationToken"]

    return MigrationResult(
        stats=stats,
        continuation_token=None,
        has_more=False,
    )


def migrate_stage_2(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
    continuation_token: str | None = None,
) -> MigrationResult:
    """Copy thumb_*.png to thumb_*.jpg (verify JPEG format first).

    Processes up to batch_size objects before returning with a continuation token.

    Args:
        s3: Boto3 S3 client
        bucket: S3 bucket name
        dry_run: If True, don't make changes
        limit: Maximum total objects to process (for testing)
        errors: List to append error dicts to
        batch_size: Objects to process before returning (default 500)
        continuation_token: Token from previous call to resume

    Returns:
        MigrationResult with stats and continuation token (None if complete)
    """
    stats = {
        "processed": 0,
        "copied": 0,
        "already_exists": 0,
        "skipped_not_jpeg": 0,
        "errors": 0,
    }
    current_token = continuation_token

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": f"{S3_IMAGES_PREFIX}thumb_",
            "MaxKeys": 1000,
        }
        if current_token:
            kwargs["ContinuationToken"] = current_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".png"):
                continue

            # Check limit
            if limit and stats["processed"] >= limit:
                return MigrationResult(
                    stats=stats,
                    continuation_token=None,
                    has_more=False,
                )

            # Check batch size - return early with continuation token
            if stats["processed"] >= batch_size:
                next_token = (
                    response.get("NextContinuationToken") if response.get("IsTruncated") else None
                )
                return MigrationResult(
                    stats=stats,
                    continuation_token=current_token or next_token,
                    has_more=True,
                )

            try:
                new_key = key.rsplit(".", 1)[0] + ".jpg"

                # Check if .jpg already exists (idempotent)
                try:
                    s3.head_object(Bucket=bucket, Key=new_key)
                    stats["already_exists"] += 1
                    stats["processed"] += 1
                    continue
                except ClientError:
                    pass  # Doesn't exist, proceed

                # Verify it's actually JPEG format
                range_resp = s3.get_object(Bucket=bucket, Key=key, Range="bytes=0-11")
                magic_bytes = range_resp["Body"].read()

                # Handle truncated/corrupt images with insufficient bytes
                if len(magic_bytes) < MIN_DETECTION_BYTES:
                    logger.warning(
                        f"Skipping {key}: truncated or corrupt "
                        f"(only {len(magic_bytes)} bytes, need {MIN_DETECTION_BYTES})"
                    )
                    errors.append(
                        {
                            "key": key,
                            "error": f"Truncated/corrupt: only {len(magic_bytes)} bytes",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    stats["skipped_not_jpeg"] += 1
                    stats["processed"] += 1
                    continue

                actual_format = detect_format(magic_bytes, strict=False)

                if actual_format != ImageFormat.JPEG:
                    errors.append(
                        {
                            "key": key,
                            "error": f"Expected JPEG but found {actual_format.value}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    stats["skipped_not_jpeg"] += 1
                    stats["processed"] += 1
                    continue

                if not dry_run:
                    s3.copy_object(
                        Bucket=bucket,
                        CopySource={"Bucket": bucket, "Key": key},
                        Key=new_key,
                        MetadataDirective="REPLACE",
                        ContentType="image/jpeg",
                    )
                stats["copied"] += 1
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Copied {key} -> {new_key}")

            except ClientError as e:
                errors.append(
                    {
                        "key": key,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                stats["errors"] += 1

            stats["processed"] += 1

        if not response.get("IsTruncated"):
            break
        current_token = response["NextContinuationToken"]

    return MigrationResult(
        stats=stats,
        continuation_token=None,
        has_more=False,
    )


def cleanup_stage_3(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
    continuation_token: str | None = None,
) -> MigrationResult:
    """Delete thumb_*.png after verifying .jpg exists.

    If bucket versioning is enabled, deletes all versions of each .png file
    to prevent paying for old versions with wrong metadata indefinitely.

    Processes up to batch_size objects before returning with a continuation token.

    Args:
        s3: Boto3 S3 client
        bucket: S3 bucket name
        dry_run: If True, don't make changes
        limit: Maximum total objects to process (for testing)
        errors: List to append error dicts to
        batch_size: Objects to process before returning (default 500)
        continuation_token: Token from previous call to resume

    Returns:
        MigrationResult with stats and continuation token (None if complete)
    """
    stats = {
        "processed": 0,
        "deleted": 0,
        "versions_deleted": 0,
        "skipped_no_jpg": 0,
        "errors": 0,
    }
    current_token = continuation_token
    delete_batch: list[dict[str, str]] = []

    # Check if bucket has versioning enabled
    versioning_enabled = _check_bucket_versioning(s3, bucket)
    if versioning_enabled:
        logger.warning(
            f"Bucket {bucket} has versioning enabled. "
            "Will delete all versions of .png thumbnails to prevent storage costs "
            "from old versions with incorrect ContentType metadata."
        )

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": f"{S3_IMAGES_PREFIX}thumb_",
            "MaxKeys": 1000,
        }
        if current_token:
            kwargs["ContinuationToken"] = current_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".png"):
                continue

            # Check limit
            if limit and stats["processed"] >= limit:
                # Flush pending deletes before returning
                if delete_batch:
                    if dry_run:
                        stats["deleted"] += len(delete_batch)
                    else:
                        _batch_delete_with_errors(s3, bucket, delete_batch, errors, stats)
                return MigrationResult(
                    stats=stats,
                    continuation_token=None,
                    has_more=False,
                )

            # Check batch size - return early with continuation token
            if stats["processed"] >= batch_size:
                # Flush pending deletes before returning
                if delete_batch:
                    if dry_run:
                        stats["deleted"] += len(delete_batch)
                    else:
                        _batch_delete_with_errors(s3, bucket, delete_batch, errors, stats)
                next_token = (
                    response.get("NextContinuationToken") if response.get("IsTruncated") else None
                )
                return MigrationResult(
                    stats=stats,
                    continuation_token=current_token or next_token,
                    has_more=True,
                )

            try:
                jpg_key = key.rsplit(".", 1)[0] + ".jpg"

                # Only delete if .jpg exists
                try:
                    s3.head_object(Bucket=bucket, Key=jpg_key)
                except ClientError:
                    stats["skipped_no_jpg"] += 1
                    stats["processed"] += 1
                    continue

                if versioning_enabled:
                    # Delete all versions individually for versioned buckets
                    if not dry_run:
                        versions_deleted = _delete_all_versions(s3, bucket, key, errors)
                        stats["versions_deleted"] += versions_deleted
                    else:
                        logger.info(f"[DRY RUN] Would delete all versions of: {key}")
                    stats["deleted"] += 1
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleted (versioned): {key}")
                else:
                    # Use batch delete for non-versioned buckets
                    delete_batch.append({"Key": key})
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Queued delete: {key}")

                    # Batch delete every 1000 objects
                    if len(delete_batch) >= 1000:
                        if dry_run:
                            stats["deleted"] += len(delete_batch)
                        else:
                            _batch_delete_with_errors(s3, bucket, delete_batch, errors, stats)
                        delete_batch = []

            except ClientError as e:
                errors.append(
                    {
                        "key": key,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                stats["errors"] += 1

            stats["processed"] += 1

        if not response.get("IsTruncated"):
            break
        current_token = response["NextContinuationToken"]

    # Final batch (non-versioned only)
    if delete_batch:
        if dry_run:
            stats["deleted"] += len(delete_batch)
        else:
            _batch_delete_with_errors(s3, bucket, delete_batch, errors, stats)

    if versioning_enabled and stats["versions_deleted"] > 0:
        logger.info(
            f"Deleted {stats['versions_deleted']} total versions across "
            f"{stats['deleted']} objects in versioned bucket"
        )

    return MigrationResult(
        stats=stats,
        continuation_token=None,
        has_more=False,
    )
