"""Listings extraction API endpoints."""

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.listing import (
    is_valid_ebay_url,
    match_author,
    match_binder,
    match_publisher,
    normalize_ebay_url,
)
from app.services.scraper import ScraperError, ScraperRateLimitError, scrape_ebay_listing

logger = logging.getLogger(__name__)

router = APIRouter()


class ExtractRequest(BaseModel):
    """Request body for listing extraction."""

    url: str = Field(..., description="eBay listing URL")


class ImagePreview(BaseModel):
    """Image preview in response."""

    url: str
    preview: str  # base64 data URI
    content_type: str


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
    image_urls: list[str]
    matches: dict


@router.post("/extract", response_model=ExtractResponse)
def extract_listing(
    request: ExtractRequest,
    db: Session = Depends(get_db),
):
    """Extract data from an eBay listing URL.

    Scrapes the listing, extracts structured book data using AI,
    and matches against existing authors/binders/publishers.
    """
    # Validate URL
    if not is_valid_ebay_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid eBay URL")

    # Normalize URL and extract item ID
    normalized_url, item_id = normalize_ebay_url(request.url)

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

    listing_data = result["listing_data"]

    # Build image previews
    images = []
    for img in result["images"]:
        preview = f"data:{img['content_type']};base64,{base64.b64encode(img['data']).decode()}"
        images.append(
            ImagePreview(
                url=img["url"],
                preview=preview,
                content_type=img["content_type"],
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
        ebay_item_id=item_id,
        listing_data=listing_data,
        images=images,
        image_urls=result["image_urls"],
        matches=matches,
    )
