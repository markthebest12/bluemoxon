"""Image processor Lambda handler.

Processes book images to remove backgrounds and add solid backgrounds
based on book brightness.
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BRIGHTNESS_THRESHOLD = 128


def get_processing_config(attempt: int) -> dict:
    """Get rembg processing configuration for attempt number.

    Args:
        attempt: Attempt number (1, 2, or 3)

    Returns:
        Dict with model and alpha_matting settings
    """
    if attempt <= 2:
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

    if area_ratio < 0.5:
        return {"passed": False, "reason": "area_too_small"}

    original_aspect = original_width / original_height
    subject_aspect = subject_width / subject_height
    aspect_diff = abs(original_aspect - subject_aspect) / original_aspect

    if aspect_diff > 0.2:
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


def lambda_handler(event, context):
    """Lambda entry point for SQS-triggered image processing.

    Args:
        event: SQS event with Records
        context: Lambda context

    Returns:
        Dict with batchItemFailures for partial batch failure reporting
    """
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

    Args:
        job_id: ImageProcessingJob ID
        book_id: Book ID
        image_id: Source image ID

    Returns:
        True if successful
    """
    logger.info(f"Processing not yet fully implemented for job {job_id}")
    return False
