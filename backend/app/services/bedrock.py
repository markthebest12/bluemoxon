"""AWS Bedrock service for AI-powered analysis generation."""

import base64
import json  # Used in invoke_bedrock() (Task 4)
import logging
import os
import time

import boto3
import httpx
from botocore.exceptions import ClientError

from app.config import get_settings
from app.models import BookImage

logger = logging.getLogger(__name__)
settings = get_settings()

# Model ID mapping
MODEL_IDS = {
    "sonnet": "anthropic.claude-sonnet-4-5-20240929",
    "opus": "anthropic.claude-opus-4-5-20251101",
}

# Prompt cache with TTL
_prompt_cache: dict = {"prompt": None, "timestamp": 0}
PROMPT_CACHE_TTL = 300  # 5 minutes

# S3 prompt location
PROMPTS_BUCKET = os.environ.get("PROMPTS_BUCKET", settings.images_bucket)
PROMPT_KEY = "prompts/napoleon-framework/v1.md"

# Fallback prompt if S3 unavailable
FALLBACK_PROMPT = """You are an expert antiquarian book appraiser generating a Napoleon framework analysis.

Generate a comprehensive book analysis following these sections:
1. Executive Summary (50-100 lines)
2. Detailed Condition Assessment (100-200 lines)
3. Comprehensive Market Analysis (150-300 lines)
4. Market Positioning & Victorian Binding Trends (100-150 lines)
5. Binding/Publisher Historical Context (100-200 lines)
6. Binding Elaborateness Classification (50-100 lines)
7. Rarity Assessment (50-100 lines)
8. Professional Valuation Methodology (100-150 lines)
9. Insurance Recommendations (50-75 lines)
10. Preservation and Care Guidelines (75-125 lines)
11. Value Enhancement/Detraction Factors (75-100 lines)
12. Conclusions and Recommendations (50-100 lines)
13. Methodology Statement and Disclaimers (50-75 lines)

Minimum 500 lines for standard items, 700+ for high-value items.
Use markdown formatting with headers, bullet points, and tables where appropriate.
"""


def get_bedrock_client():
    """Get Bedrock runtime client."""
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("bedrock-runtime", region_name=region)


def get_s3_client():
    """Get S3 client."""
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("s3", region_name=region)


def get_model_id(model_name: str) -> str:
    """Get Bedrock model ID from friendly name."""
    return MODEL_IDS.get(model_name, MODEL_IDS["sonnet"])


def load_napoleon_prompt() -> str:
    """Load Napoleon framework prompt from S3 with caching.

    Returns cached prompt if still valid, otherwise fetches from S3.
    Falls back to hardcoded prompt if S3 unavailable.
    """
    global _prompt_cache

    current_time = time.time()

    # Return cached prompt if still valid
    if _prompt_cache["prompt"] and (current_time - _prompt_cache["timestamp"]) < PROMPT_CACHE_TTL:
        logger.debug("Using cached Napoleon prompt")
        return _prompt_cache["prompt"]

    # Try to load from S3
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=PROMPT_KEY)
        prompt = response["Body"].read().decode("utf-8")
        logger.info(f"Loaded Napoleon prompt from s3://{PROMPTS_BUCKET}/{PROMPT_KEY}")

        # Update cache
        _prompt_cache = {"prompt": prompt, "timestamp": current_time}
        return prompt

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(f"Failed to load prompt from S3 ({error_code}), using fallback")
        return FALLBACK_PROMPT
    except Exception as e:
        logger.warning(f"Error loading prompt from S3: {e}, using fallback")
        return FALLBACK_PROMPT


def clear_prompt_cache():
    """Clear the prompt cache (useful for testing)."""
    global _prompt_cache
    _prompt_cache = {"prompt": None, "timestamp": 0}


def fetch_source_url_content(url: str | None, timeout: int = 15) -> str | None:
    """Fetch content from a source URL (eBay listing, AbeBooks, etc).

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Text content of the page, or None if fetch failed
    """
    if not url:
        return None

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; BlueMoxon/1.0)"
            })
            response.raise_for_status()

            # Return text content (HTML)
            content = response.text

            # Truncate if too long (Bedrock has token limits)
            max_chars = 50000  # ~12k tokens
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[Content truncated...]"

            logger.info(f"Fetched {len(content)} chars from {url}")
            return content

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {url}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None


def format_image_for_bedrock(image_data: bytes, media_type: str) -> dict:
    """Format image data for Bedrock Claude message API.

    Args:
        image_data: Raw image bytes
        media_type: MIME type (e.g., "image/jpeg")

    Returns:
        Dict in Bedrock image content block format
    """
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(image_data).decode("utf-8"),
        },
    }


def fetch_book_images_for_bedrock(
    images: list[BookImage],
    max_images: int = 10,
) -> list[dict]:
    """Fetch book images from S3 and format for Bedrock.

    Args:
        images: List of BookImage objects
        max_images: Maximum number of images to include

    Returns:
        List of Bedrock-formatted image content blocks
    """
    if not images:
        return []

    result = []
    s3 = get_s3_client()
    bucket = os.environ.get("IMAGES_BUCKET", settings.images_bucket)

    # Sort by display_order and take max_images
    sorted_images = sorted(images, key=lambda x: x.display_order)[:max_images]

    for img in sorted_images:
        try:
            # Fetch from S3
            s3_key = f"books/{img.s3_key}"
            response = s3.get_object(Bucket=bucket, Key=s3_key)
            image_data = response["Body"].read()

            # Determine media type from S3 ContentType, fallback to filename extension
            content_type = response.get("ContentType")
            if not content_type or content_type == "application/octet-stream":
                # S3 metadata missing or generic, infer from filename
                if img.s3_key.lower().endswith(".png"):
                    content_type = "image/png"
                elif img.s3_key.lower().endswith((".jpg", ".jpeg")):
                    content_type = "image/jpeg"
                else:
                    content_type = "image/jpeg"  # Default

            result.append(format_image_for_bedrock(image_data, content_type))
            logger.debug(f"Loaded image {img.s3_key} for Bedrock")

        except Exception as e:
            logger.warning(f"Failed to load image {img.s3_key}: {e}")
            continue

    logger.info(f"Loaded {len(result)} images for Bedrock analysis")
    return result
