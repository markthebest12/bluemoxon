"""Listings extraction API endpoints."""

import json
import logging
import os
from typing import Literal
from urllib.parse import urlparse

import boto3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.listing import (
    extract_listing_data,
    is_valid_ebay_url,
    match_author,
    match_binder,
    match_publisher,
    normalize_ebay_url,
)
from app.services.scraper import (
    PRESIGNED_URL_EXPIRY,
    ScraperError,
    ScraperRateLimitError,
    generate_presigned_url,
    scrape_ebay_listing,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# S3 bucket for images
IMAGES_BUCKET = os.environ.get("IMAGES_BUCKET", "")

# Lambda function name pattern
SCRAPER_FUNCTION_NAME = "bluemoxon-{environment}-scraper"


def is_ebay_short_url(url: str) -> bool:
    """Check if URL is an ebay.us short URL that needs scraper-based resolution.

    These URLs can't be resolved via httpx from Lambda (timeout issues),
    so we let the scraper Lambda handle the redirect via Playwright.
    """
    try:
        parsed = urlparse(url)
        return "ebay.us" in parsed.netloc.lower()
    except Exception:
        return False


class ExtractRequest(BaseModel):
    """Request body for listing extraction."""

    url: str = Field(..., description="eBay listing URL")


class ImagePreview(BaseModel):
    """Image preview in response.

    Images are stored in S3 and accessed via presigned URLs.
    """

    s3_key: str  # S3 object key (e.g., "listings/317651598134/image_00.webp")
    presigned_url: str  # Presigned URL for direct access (expires in 1 hour)


class ReferenceMatch(BaseModel):
    """Reference match result."""

    id: int
    name: str
    similarity: float


class ExtractResponse(BaseModel):
    """Response from listing extraction."""

    ebay_url: str
    ebay_item_id: str
    listing_data: dict
    images: list[ImagePreview]
    image_urls: list[str]  # Original eBay image URLs (for reference)
    matches: dict


@router.post("/extract", response_model=ExtractResponse)
def extract_listing(
    request: ExtractRequest,
    db: Session = Depends(get_db),
):
    """Extract data from an eBay listing URL.

    Scrapes the listing, extracts structured book data using AI,
    uploads images to S3, and matches against existing authors/binders/publishers.

    Images are uploaded to S3 at listings/{item_id}/ and returned as presigned URLs.
    """
    # Validate URL
    if not is_valid_ebay_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid eBay URL")

    # For ebay.us short URLs, skip normalize_ebay_url (times out from Lambda VPC)
    # and let the scraper handle the redirect via Playwright
    if is_ebay_short_url(request.url):
        logger.info(f"Short URL detected, letting scraper handle redirect: {request.url}")
        normalized_url = None  # Will be set from scraper result
        item_id = None
    else:
        # Normalize URL and extract item ID (can raise ValueError for expired short URLs)
        try:
            normalized_url, item_id = normalize_ebay_url(request.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        # Scrape and extract
        result = scrape_ebay_listing(request.url)
    except ScraperRateLimitError as e:
        logger.warning(f"Rate limited: {e}")
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {e}") from e
    except ScraperError as e:
        logger.error(f"Scraper error: {e}")
        raise HTTPException(status_code=502, detail=f"Scraping failed: {e}") from e
    except ValueError as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=422, detail=f"Failed to extract listing data: {e}") from e

    # For short URLs, get the item_id from scraper result and build normalized URL
    scraper_item_id = result.get("item_id", "")
    if not normalized_url and scraper_item_id:
        item_id = scraper_item_id
        normalized_url = f"https://www.ebay.com/itm/{item_id}"
    elif not normalized_url:
        raise HTTPException(status_code=422, detail="Could not extract item ID from short URL")

    listing_data = result["listing_data"]

    # Build image previews from S3 presigned URLs
    images = []
    for img in result["images"]:
        images.append(
            ImagePreview(
                s3_key=img["s3_key"],
                presigned_url=img["presigned_url"],
            )
        )

    # Match references
    matches = {}

    if listing_data.get("author"):
        author_match = match_author(listing_data["author"], db)
        if author_match:
            matches["author"] = author_match

    if listing_data.get("binder"):
        binder_match = match_binder(listing_data["binder"], db)
        if binder_match:
            matches["binder"] = binder_match

    if listing_data.get("publisher"):
        publisher_match = match_publisher(listing_data["publisher"], db)
        if publisher_match:
            matches["publisher"] = publisher_match

    return ExtractResponse(
        ebay_url=normalized_url,
        ebay_item_id=result.get("item_id", item_id),
        listing_data=listing_data,
        images=images,
        image_urls=result["image_urls"],
        matches=matches,
    )


# =============================================================================
# Async Extraction Endpoints
# =============================================================================


class ExtractAsyncResponse(BaseModel):
    """Response from async extraction initiation."""

    item_id: str
    status: Literal["started", "already_scraped"]
    message: str


class ExtractStatusResponse(BaseModel):
    """Response from extraction status check."""

    item_id: str
    status: Literal["pending", "scraped", "ready", "error"]
    ebay_url: str | None = None
    listing_data: dict | None = None
    images: list[ImagePreview] = []
    matches: dict = {}
    error: str | None = None


@router.post("/extract-async", response_model=ExtractAsyncResponse, status_code=202)
def extract_listing_async(
    request: ExtractRequest,
):
    """Start async extraction of an eBay listing.

    Kicks off the scraper Lambda asynchronously and returns immediately.
    Poll /extract/{item_id}/status for results.
    """
    # Validate URL
    if not is_valid_ebay_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid eBay URL")

    # Short URLs not supported for async extraction (can't get item_id without scraping)
    # Use the sync /extract endpoint instead
    if is_ebay_short_url(request.url):
        raise HTTPException(
            status_code=400,
            detail="Short URLs (ebay.us) are not supported for async extraction. "
            "Please use the /extract endpoint instead.",
        )

    # Normalize URL and extract item ID (can raise ValueError for expired short URLs)
    try:
        normalized_url, item_id = normalize_ebay_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Check if already scraped (images exist in S3)
    s3 = boto3.client("s3")
    try:
        # Check for at least one image
        response = s3.list_objects_v2(
            Bucket=IMAGES_BUCKET,
            Prefix=f"listings/{item_id}/",
            MaxKeys=1,
        )
        already_scraped = response.get("KeyCount", 0) > 0
    except Exception as e:
        logger.warning(f"Error checking S3 for existing images: {e}")
        already_scraped = False

    if already_scraped:
        return ExtractAsyncResponse(
            item_id=item_id,
            status="already_scraped",
            message="Images already exist. Check /extract/{item_id}/status for results.",
        )

    # Invoke scraper Lambda asynchronously
    environment = os.getenv("ENVIRONMENT", "staging")
    function_name = SCRAPER_FUNCTION_NAME.format(environment=environment)

    lambda_client = boto3.client("lambda")
    payload = {"url": request.url, "fetch_images": True}

    try:
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",  # Async invocation
            Payload=json.dumps(payload),
        )
        logger.info(f"Started async scraper for {item_id}")
    except Exception as e:
        logger.error(f"Failed to invoke scraper Lambda: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to start scraper: {e}") from None

    return ExtractAsyncResponse(
        item_id=item_id,
        status="started",
        message="Scraper started. Poll /extract/{item_id}/status for results.",
    )


@router.get("/extract/{item_id}/status", response_model=ExtractStatusResponse)
def get_extract_status(
    item_id: str,
    db: Session = Depends(get_db),
):
    """Get status of an async extraction job.

    Returns 'pending' if scraper still running, 'scraped' if images exist but not extracted,
    'ready' if extraction complete with listing data and matches.
    """
    s3 = boto3.client("s3")

    # Check if images exist in S3
    try:
        response = s3.list_objects_v2(
            Bucket=IMAGES_BUCKET,
            Prefix=f"listings/{item_id}/",
        )
        s3_keys = [obj["Key"] for obj in response.get("Contents", [])]
    except Exception as e:
        logger.error(f"Error checking S3 for images: {e}")
        return ExtractStatusResponse(
            item_id=item_id,
            status="error",
            error=f"S3 error: {e}",
        )

    # Filter out page.html from s3_keys (we only want images)
    html_key = f"listings/{item_id}/page.html"
    image_s3_keys = [k for k in s3_keys if k != html_key]
    has_html = html_key in s3_keys

    # HTML is uploaded LAST by scraper, so if we don't have HTML yet,
    # the scraper is still uploading images
    if not has_html or not image_s3_keys:
        # Scraper still running - either no images or no HTML yet
        return ExtractStatusResponse(
            item_id=item_id,
            status="pending",
        )

    ebay_url = f"https://www.ebay.com/itm/{item_id}"

    # Read HTML from S3 (uploaded by scraper Lambda)
    html = None
    if html_key in s3_keys:
        try:
            response = s3.get_object(Bucket=IMAGES_BUCKET, Key=html_key)
            html = response["Body"].read().decode("utf-8")
            logger.info(f"Read HTML from S3: {len(html)} chars")
        except Exception as e:
            logger.warning(f"Failed to read HTML from S3: {e}")

    # Fallback: fetch from eBay if HTML not in S3 (legacy items)
    if not html:
        logger.warning(f"HTML not found in S3 for {item_id}, falling back to httpx fetch")
        try:
            import httpx

            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    ebay_url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; BlueMoxon/1.0)"},
                    follow_redirects=True,
                )
                html = resp.text
        except Exception as e:
            logger.error(f"Failed to fetch eBay page: {e}")
            return ExtractStatusResponse(
                item_id=item_id,
                status="error",
                error=f"Failed to fetch listing: {e}",
            )

    # Extract structured data using Bedrock
    try:
        listing_data = extract_listing_data(html)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return ExtractStatusResponse(
            item_id=item_id,
            status="error",
            error=f"Extraction failed: {e}",
        )

    # Build image previews with presigned URLs (exclude page.html)
    images = []
    for s3_key in sorted(image_s3_keys):
        try:
            presigned_url = generate_presigned_url(IMAGES_BUCKET, s3_key, PRESIGNED_URL_EXPIRY)
            images.append(ImagePreview(s3_key=s3_key, presigned_url=presigned_url))
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL for {s3_key}: {e}")

    # Match references
    matches = {}

    if listing_data.get("author"):
        author_match = match_author(listing_data["author"], db)
        if author_match:
            matches["author"] = author_match

    if listing_data.get("binder"):
        binder_match = match_binder(listing_data["binder"], db)
        if binder_match:
            matches["binder"] = binder_match

    if listing_data.get("publisher"):
        publisher_match = match_publisher(listing_data["publisher"], db)
        if publisher_match:
            matches["publisher"] = publisher_match

    return ExtractStatusResponse(
        item_id=item_id,
        status="ready",
        ebay_url=ebay_url,
        listing_data=listing_data,
        images=images,
        matches=matches,
    )
