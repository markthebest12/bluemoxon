"""Image processor Lambda handler.

Processes book images to remove backgrounds and add solid backgrounds
based on book brightness.
"""

import io
import json
import logging
import os
import uuid
from datetime import UTC, datetime

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

# Minimum subject area as ratio of original image area (0.0-1.0)
# Subject smaller than this ratio fails quality validation
MIN_AREA_RATIO = 0.5

# Maximum aspect ratio difference tolerance (0.0-1.0)
# Aspect ratio change greater than this fails quality validation
MAX_ASPECT_DIFF = 0.2

# Maximum input image dimension (width or height) in pixels
# Images larger than this are rejected to prevent OOM
MAX_IMAGE_DIMENSION = 4096

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

    Caches the result to avoid repeated Secrets Manager calls on warm invocations.
    """
    global _db_secret_cache
    if _db_secret_cache is not None:
        return _db_secret_cache

    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=secret_arn)
    _db_secret_cache = json.loads(response["SecretString"])
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


def validate_image_quality(
    original_width: int,
    original_height: int,
    subject_width: int,
    subject_height: int,
) -> dict:
    """Validate processed image quality.

    Args:
        original_width: Original image width
        original_height: Original image height
        subject_width: Extracted subject width
        subject_height: Extracted subject height

    Returns:
        Dict with passed (bool) and reason (str if failed)
    """
    original_area = original_width * original_height
    subject_area = subject_width * subject_height
    area_ratio = subject_area / original_area

    if area_ratio < MIN_AREA_RATIO:
        return {"passed": False, "reason": "area_too_small"}

    original_aspect = original_width / original_height
    subject_aspect = subject_width / subject_height
    aspect_diff = abs(original_aspect - subject_aspect) / original_aspect

    if aspect_diff > MAX_ASPECT_DIFF:
        return {"passed": False, "reason": "aspect_ratio_mismatch"}

    return {"passed": True, "reason": None}


def select_background_color(brightness: int) -> str:
    """Select background color based on image brightness.

    Args:
        brightness: Average brightness (0-255)

    Returns:
        "black" or "white"
    """
    return "black" if brightness < BRIGHTNESS_THRESHOLD else "white"


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

    Args:
        image: RGBA PIL Image

    Returns:
        Average brightness (0-255)
    """
    if image.mode != "RGBA":
        grayscale = image.convert("L")
        pixels = list(grayscale.getdata())
        if not pixels:
            return 128
        return sum(pixels) // len(pixels)

    pixels = list(image.getdata())
    brightness_values = []

    for r, g, b, a in pixels:
        if a > 0:
            luminance = int(0.299 * r + 0.587 * g + 0.114 * b)
            brightness_values.append(luminance)

    if not brightness_values:
        return 128

    return sum(brightness_values) // len(brightness_values)


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

    db = None
    try:
        db = get_db_session()

        job = db.query(ImageProcessingJob).filter(ImageProcessingJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return False

        job.status = "processing"
        db.commit()

        source_image = db.query(BookImage).filter(BookImage.id == image_id).first()
        if not source_image:
            job.status = "failed"
            job.failure_reason = "Source image not found"
            job.completed_at = datetime.now(UTC)
            db.commit()
            return False

        s3_key = source_image.s3_key
        if not s3_key.startswith("books/"):
            s3_key = f"books/{s3_key}"

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

                validation = validate_image_quality(
                    original_width,
                    original_height,
                    result["subject_width"],
                    result["subject_height"],
                )
                if not validation["passed"]:
                    logger.warning(f"Attempt {attempt} failed validation: {validation['reason']}")
                    continue

                processed_image = result["image"]
                model_used = config["model_name"]
                logger.info(f"Attempt {attempt} succeeded with model {model_used}")
                break
            except Exception as e:
                logger.exception(f"Attempt {attempt} failed with exception: {e}")
                continue

        if processed_image is None:
            job.status = "failed"
            job.failure_reason = "All processing attempts failed quality validation"
            job.completed_at = datetime.now(UTC)
            db.commit()
            logger.warning(f"Job {job_id}: all attempts failed, keeping original as primary")
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

        # CloudFront URL uses full S3 path (CloudFront origin maps to bucket root)
        cdn_url = None
        if IMAGES_CDN_DOMAIN:
            cdn_url = f"https://{IMAGES_CDN_DOMAIN}/{full_s3_key}"

        # Get existing images (excluding source) to renumber them
        existing_images = (
            db.query(BookImage)
            .filter(BookImage.book_id == book_id, BookImage.id != image_id)
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
        if db:
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
    finally:
        if db:
            db.close()
