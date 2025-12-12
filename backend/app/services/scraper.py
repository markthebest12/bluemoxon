"""Scraper invocation service for eBay listings."""

import base64
import json
import logging
import os

from app.services.listing import extract_listing_data

logger = logging.getLogger(__name__)

# Lambda function name pattern
SCRAPER_FUNCTION_NAME = "bluemoxon-{environment}-scraper"


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


def invoke_scraper(url: str, fetch_images: bool = True) -> dict:
    """Invoke the scraper Lambda to fetch an eBay listing.

    Args:
        url: eBay listing URL
        fetch_images: Whether to download images (default True)

    Returns:
        Dict with html, image_urls, and images

    Raises:
        ScraperRateLimitError: If eBay rate limits the request
        ScraperError: If scraping fails
    """
    client = get_lambda_client()
    environment = os.getenv("ENVIRONMENT", "staging")
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

    logger.info(f"Scraper returned {len(body.get('images', []))} images")
    return body


def scrape_ebay_listing(url: str) -> dict:
    """Scrape an eBay listing and extract structured data.

    High-level function that invokes the scraper and extracts listing data.

    Args:
        url: eBay listing URL

    Returns:
        Dict with:
            - listing_data: Extracted book metadata
            - images: List of decoded images with data, content_type, url
            - image_urls: List of all image URLs found

    Raises:
        ScraperRateLimitError: If eBay rate limits the request
        ScraperError: If scraping fails
        ValueError: If extraction fails
    """
    # Invoke scraper Lambda
    scraper_result = invoke_scraper(url)

    # Extract structured data from HTML
    listing_data = extract_listing_data(scraper_result["html"])

    # Decode base64 images
    images = []
    for img in scraper_result.get("images", []):
        decoded = base64.b64decode(img["base64"])
        images.append(
            {"url": img["url"], "data": decoded, "content_type": img["content_type"]}
        )

    return {
        "listing_data": listing_data,
        "images": images,
        "image_urls": scraper_result.get("image_urls", []),
    }
