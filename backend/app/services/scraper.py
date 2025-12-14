"""Scraper invocation service for eBay listings."""

import json
import logging
import os

from app.services.listing import extract_listing_data

logger = logging.getLogger(__name__)

# Lambda function name pattern
SCRAPER_FUNCTION_NAME = "bluemoxon-{environment}-scraper"

# Presigned URL expiration (1 hour)
PRESIGNED_URL_EXPIRY = 3600


class ScraperError(Exception):
    """Base exception for scraper errors."""

    pass


class ScraperRateLimitError(ScraperError):
    """Raised when eBay rate limits the request."""

    pass


def get_lambda_client():
    """Get boto3 Lambda client."""
    import boto3

    return boto3.client("lambda")


def get_s3_client():
    """Get boto3 S3 client."""
    import boto3

    return boto3.client("s3")


def generate_presigned_url(bucket: str, key: str, expiry: int = PRESIGNED_URL_EXPIRY) -> str:
    """Generate a presigned URL for an S3 object.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiry: URL expiration time in seconds

    Returns:
        Presigned URL string
    """
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiry,
    )


def invoke_scraper(url: str, fetch_images: bool = True) -> dict:
    """Invoke the scraper Lambda to fetch an eBay listing.

    Args:
        url: eBay listing URL
        fetch_images: Whether to download and upload images to S3 (default True)

    Returns:
        Dict with html, image_urls, s3_keys, and item_id

    Raises:
        ScraperRateLimitError: If eBay rate limits the request
        ScraperError: If scraping fails
    """
    client = get_lambda_client()
    environment = os.getenv("BMX_ENVIRONMENT", "staging")
    function_name = SCRAPER_FUNCTION_NAME.format(environment=environment)

    payload = {"url": url, "fetch_images": fetch_images}

    logger.info(f"Invoking scraper Lambda for {url}")
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    # Check for Lambda execution error
    if response.get("FunctionError"):
        error_payload = json.loads(response["Payload"].read())
        error_msg = error_payload.get("errorMessage", "Unknown error")
        logger.error(f"Lambda execution failed: {error_msg}")
        raise ScraperError(f"Lambda execution failed: {error_msg}")

    # Parse Lambda response
    result = json.loads(response["Payload"].read())
    status_code = result.get("statusCode", 500)
    body = json.loads(result.get("body", "{}"))

    if status_code == 429:
        logger.warning("Rate limited by eBay")
        raise ScraperRateLimitError(body.get("error", "Rate limited"))

    if status_code >= 400:
        error_msg = body.get("error", "Scraping failed")
        logger.error(f"Scraper error: {error_msg}")
        raise ScraperError(error_msg)

    logger.info(f"Scraper uploaded {len(body.get('s3_keys', []))} images to S3")
    return body


def scrape_ebay_listing(url: str) -> dict:
    """Scrape an eBay listing and extract structured data.

    High-level function that invokes the scraper and extracts listing data.
    Images are uploaded to S3 by the scraper; this function returns presigned URLs.

    Args:
        url: eBay listing URL

    Returns:
        Dict with:
            - listing_data: Extracted book metadata
            - images: List of dicts with s3_key and presigned_url
            - image_urls: List of original eBay image URLs found
            - item_id: eBay item ID

    Raises:
        ScraperRateLimitError: If eBay rate limits the request
        ScraperError: If scraping fails
        ValueError: If extraction fails
    """
    # Invoke scraper Lambda
    scraper_result = invoke_scraper(url)

    # Extract structured data from HTML
    listing_data = extract_listing_data(scraper_result["html"])

    # Generate presigned URLs for S3 images
    images = []
    bucket_name = os.getenv("IMAGES_BUCKET")
    s3_keys = scraper_result.get("s3_keys", [])

    if bucket_name and s3_keys:
        for s3_key in s3_keys:
            try:
                presigned_url = generate_presigned_url(bucket_name, s3_key)
                images.append(
                    {
                        "s3_key": s3_key,
                        "presigned_url": presigned_url,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL for {s3_key}: {e}")
    else:
        logger.warning(f"No bucket ({bucket_name}) or s3_keys ({len(s3_keys)}) for presigned URLs")

    return {
        "listing_data": listing_data,
        "images": images,
        "image_urls": scraper_result.get("image_urls", []),
        "item_id": scraper_result.get("item_id", ""),
    }
