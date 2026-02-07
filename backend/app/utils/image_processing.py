"""Image download, processing, and upload pipeline for entity portraits.

Handles downloading portrait images from Wikimedia Commons, resizing to
400x400 JPEG with EXIF rotation, and uploading to S3. Used by
portrait_sync.py for the download-process-upload pipeline.
"""

import io
import logging
from urllib.parse import quote, unquote

import httpx
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.aws_clients import get_s3_client
from app.services.wikidata_client import USER_AGENT, extract_filename_from_commons_url
from app.utils.cdn import get_cloudfront_cdn_url

logger = logging.getLogger(__name__)

# Wikimedia Commons file URL template (400px wide)
COMMONS_FILE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=400"

# Portrait dimensions and quality
PORTRAIT_SIZE = (400, 400)
PORTRAIT_QUALITY = 85

# S3 prefix for entity portraits
S3_ENTITIES_PREFIX = "entities/"


def download_portrait(image_url: str) -> bytes | None:
    """Download portrait image from Wikimedia Commons.

    Args:
        image_url: Full Wikimedia Commons image URL.

    Returns:
        Image bytes or None on failure.
    """
    filename = extract_filename_from_commons_url(image_url)
    # Decode first to avoid double-encoding (Wikidata returns pre-encoded URLs)
    url = COMMONS_FILE_URL.format(filename=quote(unquote(filename), safe=""))

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError:
        logger.exception("Failed to download portrait from %s", url)
        return None


def process_portrait(image_bytes: bytes) -> bytes | None:
    """Resize portrait to 400x400 JPEG.

    Maintains aspect ratio via thumbnail, converts to RGB, applies EXIF rotation.

    Returns:
        JPEG bytes or None on failure.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Apply EXIF orientation
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            # Resize maintaining aspect ratio
            img.thumbnail(PORTRAIT_SIZE, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            img.save(output, "JPEG", quality=PORTRAIT_QUALITY, optimize=True)
            return output.getvalue()
    except Exception:
        logger.exception("Failed to process portrait image")
        return None


def upload_to_s3(image_bytes: bytes, entity_type: str, entity_id: int) -> str:
    """Upload portrait JPEG to S3. Returns the S3 key."""
    settings = get_settings()
    s3 = get_s3_client()
    s3_key = f"{S3_ENTITIES_PREFIX}{entity_type}/{entity_id}/portrait.jpg"

    s3.put_object(
        Bucket=settings.images_bucket,
        Key=s3_key,
        Body=image_bytes,
        ContentType="image/jpeg",
        CacheControl="public, max-age=86400, stale-while-revalidate=3600",
    )
    return s3_key


def build_cdn_url(s3_key: str) -> str:
    """Build CDN URL for an entity portrait S3 key."""
    cdn_base = get_cloudfront_cdn_url()
    return f"{cdn_base}/{s3_key}"


def _download_process_upload(
    db: Session,
    entity,
    entity_type: str,
    best_candidate: dict,
    result: dict,
) -> dict:
    """Download, process, and upload portrait for a matched candidate.

    Shared pipeline for both person and publisher entities.
    """
    image_bytes = download_portrait(best_candidate["image_url"])
    if not image_bytes:
        result["status"] = "download_failed"
        return result

    processed = process_portrait(image_bytes)
    if not processed:
        result["status"] = "processing_failed"
        return result

    try:
        s3_key = upload_to_s3(processed, entity_type, entity.id)
        cdn_url = build_cdn_url(s3_key)

        entity.image_url = cdn_url
        db.flush()

        result["status"] = "uploaded"
        result["image_uploaded"] = True
        result["s3_key"] = s3_key
        result["cdn_url"] = cdn_url
    except Exception:
        logger.exception("S3 upload failed for %s/%s", entity_type, entity.id)
        result["status"] = "upload_failed"
        result["error"] = "S3 upload failed"

    return result
