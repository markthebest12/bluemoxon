"""Image processor Lambda handler.

Processes book images to remove backgrounds and add solid backgrounds
based on book brightness.
"""

import io
import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import PurePath

import boto3
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Lazy-loaded rembg functions (deferred to avoid ONNX Runtime init at module load)
_rembg_new_session = None
_rembg_remove = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# =============================================================================
# Processing Constants
# =============================================================================
# These values are intentionally set and should be displayed in admin config.
# See GitHub issue #1149 for admin display feature.

# Background color selection threshold (0-255)
# Images with average brightness below this get black background, above get white
BRIGHTNESS_THRESHOLD = 128

# Maximum processing attempts before marking job as failed
MAX_ATTEMPTS = 3

# Maximum input image dimension (width or height) in pixels
# Images larger than this are rejected to prevent OOM
MAX_IMAGE_DIMENSION = 4096

# Thumbnail settings (matches API endpoint in images.py)
THUMBNAIL_MAX_SIZE = (300, 300)
THUMBNAIL_QUALITY = 85

# Image type priority for source selection (highest priority first)
# Lambda will select best source image based on this order
IMAGE_TYPE_PRIORITY = ["title_page", "binding", "cover", "spine"]

# S3 key prefix for book images (matches API's S3_IMAGES_PREFIX)
S3_IMAGES_PREFIX = "books/"

# Attempt number at which to switch from u2net to isnet-general-use model
U2NET_FALLBACK_ATTEMPT = 3

# Environment variables
DATABASE_SECRET_ARN = os.environ.get("DATABASE_SECRET_ARN", "")
IMAGES_BUCKET = os.environ.get("IMAGES_BUCKET", "")
IMAGES_CDN_DOMAIN = os.environ.get("IMAGES_CDN_DOMAIN", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Lazy-loaded resources (cached between warm invocations)
_s3_client = None
_db_engine = None
_db_secret_cache = None  # Cache secrets to avoid repeated Secrets Manager calls
_db_secret_cache_time = 0  # Timestamp when secret was cached
SECRET_CACHE_TTL = 1800  # 30 minutes in seconds - refresh if credentials rotate
_rembg_sessions = {}
_models_loaded = False
BookImage = None
ImageProcessingJob = None


def _ensure_rembg_loaded():
    """Lazy-load rembg to defer ONNX Runtime initialization."""
    global _rembg_new_session, _rembg_remove
    if _rembg_new_session is None:
        from rembg import new_session, remove

        _rembg_new_session = new_session
        _rembg_remove = remove


def _ensure_models_loaded():
    """Lazy-load SQLAlchemy models once on cold start."""
    global _models_loaded, BookImage, ImageProcessingJob
    if not _models_loaded:
        from app.models.image import BookImage as _BookImage
        from app.models.image_processing_job import ImageProcessingJob as _ImageProcessingJob

        BookImage = _BookImage
        ImageProcessingJob = _ImageProcessingJob
        _models_loaded = True


def get_s3_client():
    """Get or create S3 client."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def get_secret(secret_arn: str) -> dict:
    """Retrieve database credentials from Secrets Manager.

    Caches the result with TTL to avoid repeated Secrets Manager calls on warm
    invocations while ensuring rotated credentials are picked up.
    """
    global _db_secret_cache, _db_secret_cache_time, _db_engine
    current_time = time.time()

    # Return cached secret if still valid
    if _db_secret_cache is not None and (current_time - _db_secret_cache_time) < SECRET_CACHE_TTL:
        return _db_secret_cache

    # Secret expired or not cached - invalidate engine to pick up new credentials
    if _db_engine is not None:
        logger.info("Secret cache expired, invalidating DB engine for credential refresh")
        _db_engine.dispose()
        _db_engine = None

    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=secret_arn)
    _db_secret_cache = json.loads(response["SecretString"])
    _db_secret_cache_time = current_time
    return _db_secret_cache


def get_db_engine():
    """Get or create database engine."""
    global _db_engine
    if _db_engine is None:
        if not DATABASE_SECRET_ARN:
            raise ValueError("DATABASE_SECRET_ARN environment variable not set")

        secret = get_secret(DATABASE_SECRET_ARN)
        db_name = secret.get("dbname") or secret.get("database", "bluemoxon")
        database_url = (
            f"postgresql://{secret['username']}:{secret['password']}"
            f"@{secret['host']}:{secret['port']}/{db_name}"
        )
        _db_engine = create_engine(database_url, pool_pre_ping=True)
    return _db_engine


def get_db_session() -> Session:
    """Create a new database session."""
    engine = get_db_engine()
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


@contextmanager
def db_session_scope():
    """Context manager for database sessions.

    Ensures session is properly closed even if an exception occurs.
    Usage:
        with db_session_scope() as db:
            # use db
    """
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def get_processing_config(attempt: int) -> dict:
    """Get rembg processing configuration for attempt number.

    Args:
        attempt: Attempt number (1, 2, or 3)

    Returns:
        Dict with model and alpha_matting settings
    """
    if attempt < U2NET_FALLBACK_ATTEMPT:
        return {
            "model": "u2net",
            "alpha_matting": True,
            "model_name": "u2net-alpha",
        }
    else:
        return {
            "model": "isnet-general-use",
            "alpha_matting": False,
            "model_name": "isnet-general-use",
        }


def select_background_color(brightness: int) -> str:
    """Select background color based on image brightness.

    Args:
        brightness: Average brightness (0-255)

    Returns:
        "black" or "white"
    """
    return "black" if brightness < BRIGHTNESS_THRESHOLD else "white"


def normalize_s3_key(key: str) -> str:
    """Ensure S3 key has the books/ prefix for bucket operations.

    BookImage.s3_key may be stored with or without prefix for legacy reasons.
    This normalizes to always include the prefix for S3 operations.

    Args:
        key: S3 key (with or without prefix)

    Returns:
        S3 key with books/ prefix
    """
    if key.startswith(S3_IMAGES_PREFIX):
        return key
    return f"{S3_IMAGES_PREFIX}{key}"


def download_from_s3(bucket: str, key: str) -> bytes:
    """Download image from S3.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Image bytes
    """
    s3 = get_s3_client()
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def validate_image_size(width: int, height: int) -> dict:
    """Validate input image dimensions to prevent OOM.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Dict with passed (bool) and reason (str if failed)
    """
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        return {
            "passed": False,
            "reason": f"Image too large: {width}x{height} exceeds max {MAX_IMAGE_DIMENSION}px",
        }
    return {"passed": True, "reason": None}


def upload_to_s3(bucket: str, key: str, image_bytes: bytes, content_type: str) -> None:
    """Upload image to S3.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        image_bytes: Image data
        content_type: MIME content type
    """
    s3 = get_s3_client()
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=image_bytes,
        ContentType=content_type,
    )


def get_rembg_session(model_name: str):
    """Get or create rembg session for model.

    Caches sessions to avoid reloading models.
    """
    global _rembg_sessions
    _ensure_rembg_loaded()
    if model_name not in _rembg_sessions:
        _rembg_sessions[model_name] = _rembg_new_session(model_name)
    return _rembg_sessions[model_name]


def remove_background(image_bytes: bytes, config: dict) -> dict | None:
    """Remove background from image using rembg.

    Args:
        image_bytes: Original image bytes
        config: Processing config with model and alpha_matting settings

    Returns:
        Dict with image (PIL RGBA), subject_width, subject_height, or None on failure
    """
    try:
        _ensure_rembg_loaded()
        session = get_rembg_session(config["model"])
        result_bytes = _rembg_remove(
            image_bytes,
            session=session,
            alpha_matting=config.get("alpha_matting", False),
        )

        image = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

        bbox = calculate_subject_bounds(image)
        if bbox is None:
            logger.warning("No subject found after background removal")
            return None

        subject_width = bbox[2] - bbox[0]
        subject_height = bbox[3] - bbox[1]

        return {
            "image": image,
            "subject_width": subject_width,
            "subject_height": subject_height,
        }
    except Exception as e:
        logger.exception(f"Background removal failed: {e}")
        return None


def calculate_subject_bounds(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Get bounding box of non-transparent pixels.

    Args:
        image: RGBA PIL Image

    Returns:
        Tuple of (left, top, right, bottom) or None if no subject found
    """
    if image.mode != "RGBA":
        return (0, 0, image.width, image.height)

    alpha = image.split()[3]
    bbox = alpha.getbbox()
    return bbox


def calculate_brightness(image: Image.Image) -> int:
    """Calculate average brightness of non-transparent pixels.

    Uses streaming iteration to avoid loading all pixels into memory.
    For a 4096x4096 image, this uses O(1) memory instead of O(16M).

    Args:
        image: RGBA PIL Image

    Returns:
        Average brightness (0-255)
    """
    if image.mode != "RGBA":
        grayscale = image.convert("L")
        total = 0
        count = 0
        for pixel in grayscale.getdata():
            total += pixel
            count += 1
        if count == 0:
            return 128
        return total // count

    # Stream pixels without loading entire list into memory
    total = 0
    count = 0
    for r, g, b, a in image.getdata():
        if a > 0:
            total += int(0.299 * r + 0.587 * g + 0.114 * b)
            count += 1

    if count == 0:
        return 128

    return total // count


def add_background(image: Image.Image, color: str) -> Image.Image:
    """Add solid background color to RGBA image.

    Args:
        image: RGBA PIL Image
        color: "black" or "white"

    Returns:
        RGB PIL Image with background
    """
    bg_color = (0, 0, 0) if color == "black" else (255, 255, 255)
    background = Image.new("RGB", image.size, bg_color)
    background.paste(image, mask=image.split()[3])
    return background


def generate_thumbnail(image: Image.Image) -> Image.Image:
    """Generate a thumbnail from a PIL Image.

    Args:
        image: PIL Image (RGB or RGBA)

    Returns:
        Thumbnail as RGB PIL Image (JPEG-compatible)
    """
    # Convert to RGB if necessary (for PNG with transparency)
    if image.mode in ("RGBA", "P"):
        # Create white background for transparency
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "RGBA":
            background.paste(image, mask=image.split()[3])
        else:
            background.paste(image)
        image = background

    # Create thumbnail maintaining aspect ratio
    # thumbnail() modifies in place, so copy first
    thumb = image.copy()
    thumb.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)

    return thumb


def select_best_source_image(images: list, primary_image_id: int):
    """Select the best source image for processing.

    Priority order:
    1. title_page (if exists and not already processed)
    2. binding (if exists and not already processed)
    3. cover (if exists and not already processed)
    4. spine (if exists and not already processed)
    5. Primary image (fallback)
    6. Image matching primary_image_id (final fallback)

    Args:
        images: List of BookImage objects for the book
        primary_image_id: ID of the image that triggered processing

    Returns:
        Best source image to process
    """
    # Filter out already processed images
    unprocessed = [img for img in images if not getattr(img, "is_background_processed", False)]

    if not unprocessed:
        # All images processed, fall back to the requested one
        for img in images:
            if img.id == primary_image_id:
                return img
        return images[0] if images else None

    # Check for preferred image types in priority order
    for image_type in IMAGE_TYPE_PRIORITY:
        for img in unprocessed:
            if getattr(img, "image_type", None) == image_type:
                return img

    # Fall back to primary image
    for img in unprocessed:
        if getattr(img, "is_primary", False):
            return img

    # Final fallback: the image that was passed in
    for img in unprocessed:
        if img.id == primary_image_id:
            return img

    # Last resort: first unprocessed image
    return unprocessed[0]


def lambda_handler(event, context):
    """Lambda entry point for SQS-triggered image processing.

    Args:
        event: SQS event with Records
        context: Lambda context

    Returns:
        Dict with batchItemFailures for partial batch failure reporting
    """
    # Support smoke tests
    if event.get("smoke_test"):
        logger.info("Smoke test invocation")
        return {
            "statusCode": 200,
            "body": "OK",
            "version": os.environ.get("AWS_LAMBDA_FUNCTION_VERSION"),
        }

    # Normal SQS processing
    failures = []

    for record in event.get("Records", []):
        try:
            message = json.loads(record["body"])
            job_id = message["job_id"]
            book_id = message["book_id"]
            image_id = message["image_id"]

            logger.info(f"Processing job {job_id} for book {book_id}, image {image_id}")

            success = process_image(job_id, book_id, image_id)

            if not success:
                failures.append({"itemIdentifier": record["messageId"]})

        except Exception as e:
            logger.error(f"Error processing record: {e}")
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}


def process_image(job_id: str, book_id: int, image_id: int) -> bool:
    """Process a single image.

    Orchestrates the full image processing workflow:
    1. Download original from S3
    2. Try background removal with retry strategy
    3. Validate quality
    4. Calculate brightness and add background
    5. Upload processed image
    6. Update database

    Args:
        job_id: ImageProcessingJob ID
        book_id: Book ID
        image_id: Source image ID

    Returns:
        True if successful
    """
    _ensure_models_loaded()

    with db_session_scope() as db:
        try:
            job = db.query(ImageProcessingJob).filter(ImageProcessingJob.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            # Idempotency: skip if already processed or in progress (SQS at-least-once delivery)
            if job.status in ("completed", "processing"):
                logger.info(f"Job {job_id} already {job.status}, skipping (idempotent)")
                return True

            job.status = "processing"
            db.commit()

            # Get all images for this book to select best source
            # Use FOR UPDATE to prevent concurrent processing of same book
            all_images = (
                db.query(BookImage).filter(BookImage.book_id == book_id).with_for_update().all()
            )

            if not all_images:
                job.status = "failed"
                job.failure_reason = "No images found for book"
                job.completed_at = datetime.now(UTC)
                db.commit()
                return False

            # Select best source image based on type priority
            source_image = select_best_source_image(all_images, image_id)
            if source_image is None:
                job.status = "failed"
                job.failure_reason = "No valid source image found"
                job.completed_at = datetime.now(UTC)
                db.commit()
                logger.error(f"Job {job_id}: No valid source image found")
                return False

            logger.info(
                f"Selected source image {source_image.id} "
                f"(type={getattr(source_image, 'image_type', None)}, requested={image_id})"
            )

            s3_key = normalize_s3_key(source_image.s3_key)

            logger.info(f"Downloading image from s3://{IMAGES_BUCKET}/{s3_key}")
            image_bytes = download_from_s3(IMAGES_BUCKET, s3_key)
            original_image = Image.open(io.BytesIO(image_bytes))
            original_width, original_height = original_image.size

            # Validate image size to prevent OOM on very large images
            size_validation = validate_image_size(original_width, original_height)
            if not size_validation["passed"]:
                job.status = "failed"
                job.failure_reason = size_validation["reason"]
                job.completed_at = datetime.now(UTC)
                db.commit()
                logger.warning(f"Job {job_id}: {size_validation['reason']}")
                return False

            processed_image = None
            model_used = None

            for attempt in range(1, MAX_ATTEMPTS + 1):
                job.attempt_count = attempt
                db.commit()

                config = get_processing_config(attempt)
                logger.info(f"Attempt {attempt}: using model {config['model_name']}")

                try:
                    result = remove_background(image_bytes, config)
                    if result is None:
                        logger.warning(f"Attempt {attempt}: background removal returned None")
                        continue

                    # Use the result directly - no validation (matches original script behavior)
                    processed_image = result["image"]
                    model_used = config["model_name"]
                    logger.info(f"Attempt {attempt} succeeded with model {model_used}")
                    break
                except Exception as e:
                    logger.exception(f"Attempt {attempt} failed with exception: {e}")
                    continue

            if processed_image is None:
                job.status = "failed"
                job.failure_reason = "All background removal attempts failed"
                job.completed_at = datetime.now(UTC)
                db.commit()
                logger.warning(f"Job {job_id}: all rembg attempts failed")
                return False

            brightness = calculate_brightness(processed_image)
            bg_color = select_background_color(brightness)
            logger.info(f"Subject brightness: {brightness}, selected background: {bg_color}")

            final_image = add_background(processed_image, bg_color)

            # S3 key for database (without 'books/' prefix - API adds S3_IMAGES_PREFIX)
            # Format matches other images: {book_id}_{identifier}.{ext}
            db_s3_key = f"{book_id}_processed_{uuid.uuid4()}.png"
            # Full S3 key for upload (with 'books/' prefix)
            full_s3_key = f"books/{db_s3_key}"

            output_buffer = io.BytesIO()
            final_image.save(output_buffer, format="PNG", optimize=True)
            output_bytes = output_buffer.getvalue()

            logger.info(f"Uploading processed image to s3://{IMAGES_BUCKET}/{full_s3_key}")
            upload_to_s3(IMAGES_BUCKET, full_s3_key, output_bytes, "image/png")

            # Generate and upload thumbnail
            thumbnail = generate_thumbnail(final_image)
            # Use proper path manipulation for extension change
            db_s3_path = PurePath(db_s3_key)
            thumb_s3_key = f"thumb_{db_s3_path.stem}.jpg"
            full_thumb_s3_key = f"{S3_IMAGES_PREFIX}{thumb_s3_key}"

            thumb_buffer = io.BytesIO()
            thumbnail.save(thumb_buffer, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            thumb_bytes = thumb_buffer.getvalue()

            logger.info(f"Uploading thumbnail to s3://{IMAGES_BUCKET}/{full_thumb_s3_key}")
            upload_to_s3(IMAGES_BUCKET, full_thumb_s3_key, thumb_bytes, "image/jpeg")

            # CloudFront URL uses full S3 path (CloudFront origin maps to bucket root)
            cdn_url = None
            if IMAGES_CDN_DOMAIN:
                cdn_url = f"https://{IMAGES_CDN_DOMAIN}/{full_s3_key}"

            # Get existing images (excluding source image) to renumber them
            existing_images = (
                db.query(BookImage)
                .filter(BookImage.book_id == book_id, BookImage.id != source_image.id)
                .order_by(BookImage.display_order)
                .all()
            )

            # New processed image becomes primary at position 0
            new_image = BookImage(
                book_id=book_id,
                s3_key=db_s3_key,
                cloudfront_url=cdn_url,
                display_order=0,
                is_primary=True,
                is_background_processed=True,
            )
            db.add(new_image)

            # Shift existing images to positions 1, 2, 3, ... and clear is_primary
            for i, img in enumerate(existing_images):
                img.display_order = i + 1
                img.is_primary = False

            # Source image (original) goes to the end
            source_image.display_order = len(existing_images) + 1
            source_image.is_primary = False

            db.flush()

            job.status = "completed"
            job.model_used = model_used
            job.processed_image_id = new_image.id
            job.completed_at = datetime.now(UTC)

            db.commit()
            logger.info(f"Job {job_id} completed successfully, new image id: {new_image.id}")
            return True

        except Exception as e:
            logger.exception(f"Unexpected error in process_image: {e}")
            try:
                db.rollback()
                job = db.query(ImageProcessingJob).filter(ImageProcessingJob.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.failure_reason = str(e)[:1000]
                    job.completed_at = datetime.now(UTC)
                    db.commit()
            except Exception as inner_e:
                logger.error(f"Failed to update job status: {inner_e}")
            return False
