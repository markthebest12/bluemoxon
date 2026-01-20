"""Image migration service for fixing ContentType mismatches."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError

from app.utils.image_utils import (
    ImageFormat,
    detect_format,
    get_content_type,
)

logger = logging.getLogger(__name__)

S3_IMAGES_PREFIX = "books/"


async def migrate_stage_1(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
) -> dict[str, int]:
    """Fix ContentType on main images (skip thumbnails).

    Uses S3 range requests to download only first 12 bytes for format detection.
    """
    stats = {
        "processed": 0,
        "fixed": 0,
        "already_correct": 0,
        "skipped": 0,
        "errors": 0,
    }
    continuation_token = None

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": S3_IMAGES_PREFIX,
            "MaxKeys": 1000,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]

            # Skip thumbnails - handled in Stage 2
            if "/thumb_" in key:
                stats["skipped"] += 1
                continue

            if limit and stats["processed"] >= limit:
                return stats

            try:
                # Range request - only first 12 bytes
                range_resp = s3.get_object(Bucket=bucket, Key=key, Range="bytes=0-11")
                magic_bytes = range_resp["Body"].read()

                actual_format = detect_format(magic_bytes, strict=False)
                if actual_format == ImageFormat.UNKNOWN:
                    stats["skipped"] += 1
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
        continuation_token = response["NextContinuationToken"]
        await asyncio.sleep(0.1)  # Rate limiting

    return stats


async def migrate_stage_2(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
) -> dict[str, int]:
    """Copy thumb_*.png to thumb_*.jpg (verify JPEG format first)."""
    stats = {
        "processed": 0,
        "copied": 0,
        "already_exists": 0,
        "skipped_not_jpeg": 0,
        "errors": 0,
    }
    continuation_token = None

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": f"{S3_IMAGES_PREFIX}thumb_",
            "MaxKeys": 1000,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".png"):
                continue

            if limit and stats["processed"] >= limit:
                return stats

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
        continuation_token = response["NextContinuationToken"]
        await asyncio.sleep(0.1)

    return stats


async def cleanup_stage_3(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
) -> dict[str, int]:
    """Delete thumb_*.png after verifying .jpg exists (batch deletes)."""
    stats = {
        "processed": 0,
        "deleted": 0,
        "skipped_no_jpg": 0,
        "errors": 0,
    }
    continuation_token = None
    delete_batch: list[dict[str, str]] = []

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": f"{S3_IMAGES_PREFIX}thumb_",
            "MaxKeys": 1000,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".png"):
                continue

            if limit and stats["processed"] >= limit:
                # Flush pending deletes before returning
                if delete_batch and not dry_run:
                    s3.delete_objects(Bucket=bucket, Delete={"Objects": delete_batch})
                return stats

            try:
                jpg_key = key.rsplit(".", 1)[0] + ".jpg"

                # Only delete if .jpg exists
                try:
                    s3.head_object(Bucket=bucket, Key=jpg_key)
                except ClientError:
                    stats["skipped_no_jpg"] += 1
                    stats["processed"] += 1
                    continue

                delete_batch.append({"Key": key})
                stats["deleted"] += 1
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Queued delete: {key}")

                # Batch delete every 1000 objects
                if len(delete_batch) >= 1000:
                    if not dry_run:
                        s3.delete_objects(Bucket=bucket, Delete={"Objects": delete_batch})
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
        continuation_token = response["NextContinuationToken"]
        await asyncio.sleep(0.1)

    # Final batch
    if delete_batch and not dry_run:
        s3.delete_objects(Bucket=bucket, Delete={"Objects": delete_batch})

    return stats
