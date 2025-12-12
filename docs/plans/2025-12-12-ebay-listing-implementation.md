# eBay Listing Integration - Implementation Plan

## Overview

Implement Phase 4: eBay listing integration per design doc `2025-12-12-ebay-listing-integration-design.md`.

## Prerequisites

- Staging branch current with all Phase 3 scoring engine changes
- Playwright Lambda layer needs to be built/deployed
- Bedrock access confirmed (Claude Haiku for extraction)

## Task Breakdown

### Task 1: URL Utilities

**Goal:** URL normalization and parsing for eBay URLs.

**Test first:**
```python
# backend/tests/test_listing_utils.py
import pytest
from app.services.listing import normalize_ebay_url, parse_ebay_url, is_valid_ebay_url


class TestEbayUrlParsing:
    def test_standard_url(self):
        url = "https://www.ebay.com/itm/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"
        assert item_id == "317495720025"

    def test_mobile_url(self):
        url = "https://m.ebay.com/itm/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"
        assert item_id == "317495720025"

    def test_url_without_www(self):
        url = "https://ebay.com/itm/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"

    def test_url_with_slug(self):
        url = "https://www.ebay.com/itm/Antique-Book-Title/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"
        assert item_id == "317495720025"

    def test_url_with_tracking_params(self):
        url = "https://www.ebay.com/itm/317495720025?hash=item49f&mkcid=1"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"

    def test_invalid_url(self):
        with pytest.raises(ValueError, match="Invalid eBay URL"):
            normalize_ebay_url("https://amazon.com/item/123")

    def test_is_valid_ebay_url(self):
        assert is_valid_ebay_url("https://www.ebay.com/itm/123") is True
        assert is_valid_ebay_url("https://m.ebay.com/itm/123") is True
        assert is_valid_ebay_url("https://amazon.com/item/123") is False
        assert is_valid_ebay_url("not a url") is False
```

**Implementation:**
```python
# backend/app/services/listing.py
import re
from urllib.parse import urlparse, urlunparse

EBAY_HOSTS = {"ebay.com", "www.ebay.com", "m.ebay.com"}
EBAY_ITEM_PATTERN = re.compile(r"/itm/(?:[^/]+/)?(\d+)")


def is_valid_ebay_url(url: str) -> bool:
    """Check if URL is a valid eBay listing URL."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host not in EBAY_HOSTS:
            return False
        return bool(EBAY_ITEM_PATTERN.search(parsed.path))
    except Exception:
        return False


def normalize_ebay_url(url: str) -> tuple[str, str]:
    """Normalize eBay URL and extract item ID.

    Returns:
        Tuple of (normalized_url, item_id)

    Raises:
        ValueError: If URL is not a valid eBay listing URL
    """
    if not is_valid_ebay_url(url):
        raise ValueError("Invalid eBay URL")

    parsed = urlparse(url)
    match = EBAY_ITEM_PATTERN.search(parsed.path)
    item_id = match.group(1)

    # Build canonical URL
    normalized = f"https://www.ebay.com/itm/{item_id}"
    return normalized, item_id
```

**Run:** `cd backend && source .venv/bin/activate && python -m pytest tests/test_listing_utils.py -v`

**Commit:** `feat: add eBay URL normalization utilities`

---

### Task 2: Reference Matching Service

**Goal:** Fuzzy match author/publisher/binder names against existing records.

**Test first:**
```python
# backend/tests/test_reference_matching.py
import pytest
from app.services.listing import match_author, match_publisher, match_binder, normalize_name


class TestNameNormalization:
    def test_lowercase(self):
        assert normalize_name("John Ruskin") == "john ruskin"

    def test_remove_and_son(self):
        assert normalize_name("Rivière & Son") == "riviere"
        assert normalize_name("Zaehnsdorf & Co.") == "zaehnsdorf"

    def test_remove_punctuation(self):
        assert normalize_name("Smith, Elder & Co.") == "smith elder"


class TestReferenceMatching:
    def test_exact_match_author(self, db_session, sample_authors):
        # sample_authors fixture creates: John Ruskin (id=1), Charles Dickens (id=2)
        result = match_author("John Ruskin", db_session)
        assert result == {"id": 1, "name": "John Ruskin", "similarity": 1.0}

    def test_fuzzy_match_author(self, db_session, sample_authors):
        result = match_author("J. Ruskin", db_session)
        assert result["id"] == 1
        assert result["similarity"] >= 0.8

    def test_no_match_below_threshold(self, db_session, sample_authors):
        result = match_author("William Shakespeare", db_session)
        assert result is None

    def test_match_binder(self, db_session, sample_binders):
        # sample_binders: Rivière & Son (id=1), Zaehnsdorf (id=2)
        result = match_binder("Riviere", db_session)
        assert result["id"] == 1
        assert result["similarity"] >= 0.9

    def test_match_publisher(self, db_session, sample_publishers):
        result = match_publisher("Smith Elder", db_session)
        assert result is not None
```

**Implementation:**
```python
# backend/app/services/listing.py (add to existing file)
import re
from functools import lru_cache
from sqlalchemy.orm import Session
from app.models import Author, Publisher, Binder


def normalize_name(name: str) -> str:
    """Normalize a name for matching."""
    name = name.lower()
    # Remove common suffixes
    name = re.sub(r"\s*&\s*(son|co\.?|sons|company)\s*", "", name)
    name = re.sub(r"\s*(ltd\.?|limited|inc\.?)\s*", "", name)
    # Remove punctuation
    name = re.sub(r"[^\w\s]", "", name)
    # Normalize whitespace
    name = " ".join(name.split())
    return name.strip()


def jaccard_similarity(s1: str, s2: str) -> float:
    """Calculate Jaccard similarity between two strings."""
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def match_reference(
    name: str,
    records: list[tuple[int, str]],  # List of (id, name) tuples
    threshold: float = 0.9
) -> dict | None:
    """Match a name against records using fuzzy matching.

    Returns:
        Dict with id, name, similarity if match found, else None
    """
    normalized_input = normalize_name(name)
    best_match = None
    best_similarity = 0.0

    for record_id, record_name in records:
        normalized_record = normalize_name(record_name)

        # Exact match
        if normalized_input == normalized_record:
            return {"id": record_id, "name": record_name, "similarity": 1.0}

        # Fuzzy match
        similarity = jaccard_similarity(normalized_input, normalized_record)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = {"id": record_id, "name": record_name, "similarity": similarity}

    if best_match and best_similarity >= threshold:
        return best_match
    return None


def match_author(name: str, db: Session, threshold: float = 0.9) -> dict | None:
    """Match author name against database."""
    authors = db.query(Author.id, Author.name).all()
    return match_reference(name, authors, threshold)


def match_publisher(name: str, db: Session, threshold: float = 0.9) -> dict | None:
    """Match publisher name against database."""
    publishers = db.query(Publisher.id, Publisher.name).all()
    return match_reference(name, publishers, threshold)


def match_binder(name: str, db: Session, threshold: float = 0.9) -> dict | None:
    """Match binder name against database."""
    binders = db.query(Binder.id, Binder.name).all()
    return match_reference(name, binders, threshold)
```

**Run:** `python -m pytest tests/test_reference_matching.py -v`

**Commit:** `feat: add reference matching service for authors/publishers/binders`

---

### Task 3: Bedrock Listing Extraction

**Goal:** Extract structured data from listing HTML using Claude Haiku.

**Test first:**
```python
# backend/tests/test_listing_extraction.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.listing import extract_listing_data


SAMPLE_LISTING_HTML = """
<div class="x-item-title">
    <h1>The Queen of the Air by John Ruskin - Zaehnsdorf Binding 1869</h1>
</div>
<div class="x-price-primary">
    <span>US $165.00</span>
</div>
<div class="x-item-description">
    First edition. Bound by Zaehnsdorf in full crushed morocco...
</div>
"""


class TestListingExtraction:
    @patch("app.services.listing.invoke_bedrock")
    def test_extract_listing_data(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "The Queen of the Air",
            "author": "John Ruskin",
            "publisher": None,
            "binder": "Zaehnsdorf",
            "price": 165.00,
            "currency": "USD",
            "publication_date": "1869",
            "volumes": 1,
            "condition": "First edition",
            "binding": "Full crushed morocco"
        }

        result = extract_listing_data(SAMPLE_LISTING_HTML)

        assert result["title"] == "The Queen of the Air"
        assert result["author"] == "John Ruskin"
        assert result["binder"] == "Zaehnsdorf"
        assert result["price"] == 165.00
        mock_bedrock.assert_called_once()

    @patch("app.services.listing.invoke_bedrock")
    def test_handles_gbp_currency(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 125.00,
            "currency": "GBP",
        }

        result = extract_listing_data("<html>...</html>")
        assert result["currency"] == "GBP"

    @patch("app.services.listing.invoke_bedrock")
    def test_handles_missing_fields(self, mock_bedrock):
        mock_bedrock.return_value = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 100.00,
            "currency": "USD",
        }

        result = extract_listing_data("<html>...</html>")
        assert result.get("binder") is None
        assert result.get("volumes", 1) == 1
```

**Implementation:**
```python
# backend/app/services/listing.py (add to existing file)
import json
import logging
from app.services.bedrock import get_bedrock_client

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract book listing details as JSON. Return ONLY valid JSON, no explanation.

{
  "title": "book title only, no author/publisher in title",
  "author": "author name",
  "publisher": "publisher name if mentioned",
  "binder": "bindery name if mentioned (Rivière, Zaehnsdorf, Bayntun, etc.)",
  "price": 165.00,
  "currency": "USD or GBP or EUR",
  "publication_date": "year or date string",
  "volumes": 1,
  "condition": "condition notes",
  "binding": "binding description"
}

Listing HTML:
{listing_html}"""


def extract_listing_data(html: str) -> dict:
    """Extract structured book data from listing HTML using Bedrock Claude Haiku."""
    client = get_bedrock_client()

    prompt = EXTRACTION_PROMPT.format(listing_html=html[:50000])  # Truncate if too long

    response = client.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        })
    )

    response_body = json.loads(response["body"].read())
    content = response_body["content"][0]["text"]

    # Parse JSON from response
    try:
        # Handle potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response: {content}")
        raise ValueError(f"Failed to parse listing data: {e}")

    # Ensure required fields have defaults
    data.setdefault("volumes", 1)
    data.setdefault("currency", "USD")

    return data
```

**Run:** `python -m pytest tests/test_listing_extraction.py -v`

**Commit:** `feat: add Bedrock listing extraction service`

---

### Task 4: Playwright Scraper Lambda (Infrastructure)

**Goal:** Create separate Lambda for Playwright-based scraping.

**Files to create:**
```
scraper/
├── handler.py
├── requirements.txt
└── Dockerfile
```

**handler.py:**
```python
import json
import base64
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Scrape eBay listing and return HTML + images."""
    url = event.get("url")
    fetch_images = event.get("fetch_images", True)

    if not url:
        return {"statusCode": 400, "body": json.dumps({"error": "URL required"})}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Set realistic headers
            page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
            })

            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to load
            page.wait_for_selector(".x-item-title", timeout=10000)

            html = page.content()

            # Extract image URLs
            image_urls = page.evaluate("""
                () => {
                    const imgs = document.querySelectorAll('.ux-image-carousel img, .x-photos img');
                    return Array.from(imgs).map(img => img.src || img.dataset.src).filter(Boolean);
                }
            """)

            images = []
            if fetch_images:
                for img_url in image_urls[:10]:  # Max 10 images
                    try:
                        response = page.request.get(img_url)
                        if response.ok:
                            body = response.body()
                            content_type = response.headers.get("content-type", "image/jpeg")
                            images.append({
                                "url": img_url,
                                "base64": base64.b64encode(body).decode(),
                                "content_type": content_type
                            })
                    except Exception as e:
                        logger.warning(f"Failed to fetch image {img_url}: {e}")

            browser.close()

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "html": html,
                    "image_urls": image_urls,
                    "images": images
                })
            }

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

**Dockerfile:**
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY handler.py .

CMD ["handler.handler"]
```

**requirements.txt:**
```
playwright==1.40.0
```

**Terraform (add to lambda module):**
```hcl
resource "aws_lambda_function" "scraper" {
  function_name = "bluemoxon-${var.environment}-scraper"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.scraper.repository_url}:latest"

  role    = aws_iam_role.scraper_exec.arn
  timeout = 60
  memory_size = 1024

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }
}
```

**Commit:** `feat: add Playwright scraper Lambda infrastructure`

---

### Task 5: Scraper Invocation Service

**Goal:** Main API Lambda invokes scraper Lambda with fallback to httpx.

**Test first:**
```python
# backend/tests/test_scraper_service.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.listing import fetch_listing, ScraperError, RateLimitError


class TestScraperService:
    @patch("app.services.listing.invoke_scraper_lambda")
    def test_fetch_listing_success(self, mock_invoke):
        mock_invoke.return_value = {
            "html": "<html>...</html>",
            "image_urls": ["https://i.ebayimg.com/1.jpg"],
            "images": [{"url": "...", "base64": "...", "content_type": "image/jpeg"}]
        }

        result = fetch_listing("https://www.ebay.com/itm/123")
        assert "html" in result
        assert len(result["images"]) == 1

    @patch("app.services.listing.invoke_scraper_lambda")
    @patch("app.services.listing.fetch_with_httpx")
    def test_fallback_to_httpx(self, mock_httpx, mock_lambda):
        mock_lambda.side_effect = ScraperError("Lambda timeout")
        mock_httpx.return_value = {"html": "<html>...</html>", "images": []}

        result = fetch_listing("https://www.ebay.com/itm/123", method="httpx")
        mock_httpx.assert_called_once()

    @patch("app.services.listing.invoke_scraper_lambda")
    def test_rate_limit_detected(self, mock_invoke):
        mock_invoke.return_value = {
            "html": "<html>Access Denied</html>",
            "images": []
        }

        with pytest.raises(RateLimitError):
            fetch_listing("https://www.ebay.com/itm/123")
```

**Implementation:**
```python
# backend/app/services/listing.py (add to existing file)
import boto3
import json
import httpx
import os

class ScraperError(Exception):
    """Scraper failed to fetch listing."""
    pass

class RateLimitError(ScraperError):
    """eBay rate limited the request."""
    pass


def invoke_scraper_lambda(url: str, fetch_images: bool = True) -> dict:
    """Invoke the scraper Lambda function."""
    client = boto3.client("lambda")
    env = os.environ.get("ENVIRONMENT", "staging")

    response = client.invoke(
        FunctionName=f"bluemoxon-{env}-scraper",
        InvocationType="RequestResponse",
        Payload=json.dumps({"url": url, "fetch_images": fetch_images})
    )

    payload = json.loads(response["Payload"].read())

    if response.get("FunctionError"):
        raise ScraperError(f"Lambda error: {payload}")

    body = json.loads(payload.get("body", "{}"))

    if payload.get("statusCode") != 200:
        raise ScraperError(body.get("error", "Unknown error"))

    return body


def fetch_with_httpx(url: str) -> dict:
    """Fetch listing with httpx (fallback method)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()

        return {
            "html": response.text,
            "image_urls": [],  # Can't reliably get images without JS
            "images": []
        }


def detect_rate_limit(html: str) -> bool:
    """Check if response indicates rate limiting."""
    indicators = [
        "Access Denied",
        "Request blocked",
        "too many requests",
        "captcha"
    ]
    html_lower = html.lower()
    return any(indicator.lower() in html_lower for indicator in indicators)


def fetch_listing(url: str, method: str = "playwright") -> dict:
    """Fetch eBay listing content.

    Args:
        url: eBay listing URL
        method: "playwright" or "httpx"

    Returns:
        Dict with html, image_urls, images

    Raises:
        ScraperError: If fetching fails
        RateLimitError: If rate limited
    """
    if method == "playwright":
        result = invoke_scraper_lambda(url)
    else:
        result = fetch_with_httpx(url)

    if detect_rate_limit(result.get("html", "")):
        raise RateLimitError("eBay rate limited the request")

    return result
```

**Run:** `python -m pytest tests/test_scraper_service.py -v`

**Commit:** `feat: add scraper invocation service with fallback`

---

### Task 6: Extract Listing Endpoint

**Goal:** `POST /listings/extract` API endpoint with full flow.

**Test first:**
```python
# backend/tests/test_listings_api.py
import pytest
from unittest.mock import patch


class TestExtractListingEndpoint:
    @patch("app.api.v1.listings.fetch_listing")
    @patch("app.api.v1.listings.extract_listing_data")
    @patch("app.api.v1.listings.match_author")
    @patch("app.api.v1.listings.match_binder")
    def test_extract_listing_success(
        self, mock_binder, mock_author, mock_extract, mock_fetch, client, admin_token
    ):
        mock_fetch.return_value = {
            "html": "<html>...</html>",
            "images": [{"url": "...", "base64": "...", "content_type": "image/jpeg"}]
        }
        mock_extract.return_value = {
            "title": "The Queen of the Air",
            "author": "John Ruskin",
            "binder": "Zaehnsdorf",
            "price": 165.00,
            "currency": "USD",
        }
        mock_author.return_value = {"id": 42, "name": "John Ruskin", "similarity": 1.0}
        mock_binder.return_value = {"id": 5, "name": "Zaehnsdorf", "similarity": 1.0}

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "The Queen of the Air"
        assert data["author_id"] == 42
        assert data["binder_id"] == 5
        assert data["source_item_id"] == "123456"

    def test_invalid_url(self, client, admin_token):
        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://amazon.com/item/123"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "Invalid eBay URL" in response.json()["detail"]

    @patch("app.api.v1.listings.fetch_listing")
    def test_rate_limit_error(self, mock_fetch, client, admin_token):
        from app.services.listing import RateLimitError
        mock_fetch.side_effect = RateLimitError("Rate limited")

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()
```

**Implementation:**
```python
# backend/app/api/v1/listings.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.services.listing import (
    normalize_ebay_url,
    is_valid_ebay_url,
    fetch_listing,
    extract_listing_data,
    match_author,
    match_publisher,
    match_binder,
    ScraperError,
    RateLimitError,
)
from app.services.scoring import is_duplicate_title

router = APIRouter(prefix="/listings", tags=["listings"])


class ExtractRequest(BaseModel):
    url: str
    method: str = "playwright"  # or "httpx"
    listing_text: str | None = None


class ExtractResponse(BaseModel):
    source: str
    source_item_id: str
    source_url: str
    title: str
    author_name: str | None
    author_id: int | None
    publisher_name: str | None
    publisher_id: int | None
    binder_name: str | None
    binder_id: int | None
    asking_price: float | None
    currency: str
    publication_date: str | None
    volumes: int
    condition_notes: str | None
    binding_description: str | None
    image_data: list[dict]
    duplicates: list[dict]


@router.post("/extract", response_model=ExtractResponse)
def extract_listing(
    request: ExtractRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Extract structured data from an eBay listing URL."""

    # Validate and normalize URL
    if not is_valid_ebay_url(request.url):
        raise HTTPException(400, "Invalid eBay URL")

    source_url, item_id = normalize_ebay_url(request.url)

    # Fetch listing content
    try:
        if request.listing_text:
            # Manual paste fallback
            listing_html = request.listing_text
            images = []
        else:
            result = fetch_listing(source_url, method=request.method)
            listing_html = result["html"]
            images = result.get("images", [])
    except RateLimitError:
        raise HTTPException(429, "eBay rate limited. Try again in a few minutes.")
    except ScraperError as e:
        raise HTTPException(502, f"Failed to fetch listing: {e}")

    # Extract structured data
    try:
        extracted = extract_listing_data(listing_html)
    except ValueError as e:
        raise HTTPException(422, f"Failed to extract listing data: {e}")

    # Match references
    author_match = match_author(extracted.get("author", ""), db) if extracted.get("author") else None
    publisher_match = match_publisher(extracted.get("publisher", ""), db) if extracted.get("publisher") else None
    binder_match = match_binder(extracted.get("binder", ""), db) if extracted.get("binder") else None

    # Check for duplicates
    duplicates = []
    if author_match:
        from app.models import Book
        existing = db.query(Book).filter(Book.author_id == author_match["id"]).all()
        for book in existing:
            if is_duplicate_title(extracted.get("title", ""), book.title):
                duplicates.append({
                    "id": book.id,
                    "title": book.title,
                    "author": author_match["name"],
                    "similarity": 0.85  # Approximate
                })

    return ExtractResponse(
        source="ebay",
        source_item_id=item_id,
        source_url=source_url,
        title=extracted.get("title", ""),
        author_name=extracted.get("author"),
        author_id=author_match["id"] if author_match else None,
        publisher_name=extracted.get("publisher"),
        publisher_id=publisher_match["id"] if publisher_match else None,
        binder_name=extracted.get("binder"),
        binder_id=binder_match["id"] if binder_match else None,
        asking_price=extracted.get("price"),
        currency=extracted.get("currency", "USD"),
        publication_date=extracted.get("publication_date"),
        volumes=extracted.get("volumes", 1),
        condition_notes=extracted.get("condition"),
        binding_description=extracted.get("binding"),
        image_data=images,
        duplicates=duplicates[:3],
    )
```

**Register router in main.py:**
```python
from app.api.v1 import listings
app.include_router(listings.router, prefix="/api/v1")
```

**Run:** `python -m pytest tests/test_listings_api.py -v`

**Commit:** `feat: add POST /listings/extract endpoint`

---

### Task 7: Database Migration

**Goal:** Add `source_expired` and `listing_fetched_at` columns.

**Create migration:**
```bash
cd backend && alembic revision -m "add listing tracking fields"
```

**Migration file:**
```python
# backend/alembic/versions/xxxx_add_listing_tracking_fields.py
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("books", sa.Column("source_expired", sa.Boolean(), server_default="false"))
    op.add_column("books", sa.Column("listing_fetched_at", sa.DateTime()))
    op.create_index("books_source_expired_idx", "books", ["source_expired"],
                    postgresql_where=sa.text("source_expired = true"))


def downgrade():
    op.drop_index("books_source_expired_idx")
    op.drop_column("books", "listing_fetched_at")
    op.drop_column("books", "source_expired")
```

**Update model:**
```python
# backend/app/models/book.py (add fields)
source_expired: Mapped[bool] = mapped_column(Boolean, default=False)
listing_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
```

**Commit:** `feat: add listing tracking fields to books table`

---

### Task 8: Frontend Import Modal Component

**Goal:** Create `ImportListingModal.vue` component.

**Component:**
```vue
<!-- frontend/src/components/ImportListingModal.vue -->
<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Import from eBay</h2>
        <button class="close-btn" @click="close">&times;</button>
      </div>

      <div class="modal-body">
        <!-- URL Input State -->
        <div v-if="state === 'input'">
          <label>Paste eBay listing URL:</label>
          <input
            v-model="url"
            type="url"
            placeholder="https://www.ebay.com/itm/..."
            :class="{ error: urlError }"
            @keyup.enter="extract"
          />
          <p v-if="urlError" class="error-text">{{ urlError }}</p>
          <button class="primary" @click="extract" :disabled="!url">
            Extract Listing
          </button>
        </div>

        <!-- Loading State -->
        <div v-if="state === 'loading'" class="loading">
          <div class="spinner"></div>
          <p>{{ loadingMessage }}</p>
          <div class="progress-bar">
            <div class="progress" :style="{ width: progress + '%' }"></div>
          </div>
          <button class="secondary" @click="cancel">Cancel</button>
        </div>

        <!-- Rate Limited State -->
        <div v-if="state === 'rate-limited'" class="rate-limited">
          <p>⏳ Rate limited. Retrying in {{ countdown }} seconds...</p>
          <button class="secondary" @click="cancel">Cancel</button>
        </div>

        <!-- Error State -->
        <div v-if="state === 'error'" class="error-state">
          <p>⚠️ {{ errorMessage }}</p>
          <div class="error-actions">
            <button @click="retry">Retry</button>
            <button @click="tryAlternative">Try Alternative Method</button>
          </div>
          <div class="manual-fallback">
            <label>Or paste listing text manually:</label>
            <textarea v-model="manualText" rows="6"></textarea>
            <button @click="extractFromText" :disabled="!manualText">
              Extract from Text
            </button>
          </div>
        </div>

        <!-- Preview State -->
        <div v-if="state === 'preview'" class="preview">
          <div v-if="duplicates.length" class="duplicate-warning">
            ⚠️ Similar book exists: "{{ duplicates[0].title }}" ({{ Math.round(duplicates[0].similarity * 100) }}% match)
          </div>

          <div class="form-grid">
            <div class="field">
              <label>Title</label>
              <input v-model="form.title" />
            </div>
            <div class="field">
              <label>Author</label>
              <select v-model="form.author_id">
                <option :value="null">-- Select or create --</option>
                <option v-for="a in authors" :key="a.id" :value="a.id">{{ a.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>Binder</label>
              <select v-model="form.binder_id">
                <option :value="null">-- Select or create --</option>
                <option v-for="b in binders" :key="b.id" :value="b.id">{{ b.name }}</option>
              </select>
            </div>
            <div class="field-row">
              <div class="field">
                <label>Price</label>
                <input v-model.number="form.asking_price" type="number" step="0.01" />
              </div>
              <div class="field">
                <label>Currency</label>
                <select v-model="form.currency">
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                </select>
              </div>
            </div>
            <div class="field-row">
              <div class="field">
                <label>Year</label>
                <input v-model="form.publication_date" />
              </div>
              <div class="field">
                <label>Volumes</label>
                <input v-model.number="form.volumes" type="number" min="1" />
              </div>
            </div>
            <div class="field">
              <label>Binding</label>
              <textarea v-model="form.binding_description" rows="2"></textarea>
            </div>
          </div>

          <div class="images-preview" v-if="images.length">
            <label>Images ({{ images.length }})</label>
            <div class="image-grid">
              <img v-for="(img, i) in images" :key="i" :src="img.url" @click="previewImage(img)" />
            </div>
          </div>

          <div class="modal-actions">
            <button class="secondary" @click="close">Cancel</button>
            <button class="primary" @click="addToWatchlist">Add to Watchlist</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useListingsStore } from '@/stores/listings'
import { useAcquisitionsStore } from '@/stores/acquisitions'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['close', 'added'])

const listingsStore = useListingsStore()
const acquisitionsStore = useAcquisitionsStore()

type State = 'input' | 'loading' | 'rate-limited' | 'error' | 'preview'

const state = ref<State>('input')
const url = ref('')
const urlError = ref('')
const loadingMessage = ref('Fetching listing...')
const progress = ref(0)
const errorMessage = ref('')
const countdown = ref(0)
const manualText = ref('')
const method = ref<'playwright' | 'httpx'>('playwright')

const form = ref({
  title: '',
  author_id: null as number | null,
  publisher_id: null as number | null,
  binder_id: null as number | null,
  asking_price: null as number | null,
  currency: 'USD',
  publication_date: '',
  volumes: 1,
  binding_description: '',
  condition_notes: '',
  source_url: '',
  source_item_id: '',
})

const images = ref<Array<{ url: string; base64: string; content_type: string }>>([])
const duplicates = ref<Array<{ id: number; title: string; similarity: number }>>([])

// Reference data
const authors = computed(() => listingsStore.authors)
const binders = computed(() => listingsStore.binders)

async function extract() {
  if (!url.value) return

  urlError.value = ''
  state.value = 'loading'
  loadingMessage.value = 'Fetching listing...'
  progress.value = 20

  try {
    const result = await listingsStore.extractListing(url.value, method.value)

    loadingMessage.value = 'Extracting details...'
    progress.value = 60

    // Populate form
    form.value = {
      title: result.title,
      author_id: result.author_id,
      publisher_id: result.publisher_id,
      binder_id: result.binder_id,
      asking_price: result.asking_price,
      currency: result.currency,
      publication_date: result.publication_date || '',
      volumes: result.volumes,
      binding_description: result.binding_description || '',
      condition_notes: result.condition_notes || '',
      source_url: result.source_url,
      source_item_id: result.source_item_id,
    }

    images.value = result.image_data
    duplicates.value = result.duplicates

    progress.value = 100
    state.value = 'preview'
  } catch (e: any) {
    if (e.status === 429) {
      startRateLimitCountdown()
    } else {
      errorMessage.value = e.message || 'Failed to extract listing'
      state.value = 'error'
    }
  }
}

function startRateLimitCountdown() {
  state.value = 'rate-limited'
  countdown.value = method.value === 'playwright' ? 2 : 5

  const interval = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(interval)
      extract()
    }
  }, 1000)
}

function retry() {
  extract()
}

function tryAlternative() {
  method.value = 'httpx'
  extract()
}

async function extractFromText() {
  state.value = 'loading'
  loadingMessage.value = 'Extracting from text...'

  try {
    const result = await listingsStore.extractListing(url.value, 'playwright', manualText.value)
    // ... same as extract()
  } catch (e: any) {
    errorMessage.value = e.message
    state.value = 'error'
  }
}

async function addToWatchlist() {
  state.value = 'loading'
  loadingMessage.value = 'Adding to watchlist...'

  try {
    await acquisitionsStore.createFromListing({
      ...form.value,
      images: images.value,
      status: 'EVALUATING',
    })

    emit('added')
    close()
  } catch (e: any) {
    errorMessage.value = e.message
    state.value = 'error'
  }
}

function cancel() {
  state.value = 'input'
}

function close() {
  state.value = 'input'
  url.value = ''
  form.value = { /* reset */ }
  images.value = []
  duplicates.value = []
  emit('close')
}
</script>
```

**Commit:** `feat: add ImportListingModal component`

---

### Task 9: Frontend Store Actions

**Goal:** Add listings store with extract action.

```typescript
// frontend/src/stores/listings.ts
import { defineStore } from 'pinia'
import { api } from '@/lib/api'

interface ExtractedListing {
  source: string
  source_item_id: string
  source_url: string
  title: string
  author_name: string | null
  author_id: number | null
  publisher_name: string | null
  publisher_id: number | null
  binder_name: string | null
  binder_id: number | null
  asking_price: number | null
  currency: string
  publication_date: string | null
  volumes: number
  condition_notes: string | null
  binding_description: string | null
  image_data: Array<{ url: string; base64: string; content_type: string }>
  duplicates: Array<{ id: number; title: string; author: string; similarity: number }>
}

export const useListingsStore = defineStore('listings', {
  state: () => ({
    authors: [] as Array<{ id: number; name: string }>,
    publishers: [] as Array<{ id: number; name: string }>,
    binders: [] as Array<{ id: number; name: string }>,
  }),

  actions: {
    async fetchReferenceData() {
      const [authors, publishers, binders] = await Promise.all([
        api.get('/authors'),
        api.get('/publishers'),
        api.get('/binders'),
      ])
      this.authors = authors.data
      this.publishers = publishers.data
      this.binders = binders.data
    },

    async extractListing(
      url: string,
      method: 'playwright' | 'httpx' = 'playwright',
      listingText?: string
    ): Promise<ExtractedListing> {
      const response = await api.post('/listings/extract', {
        url,
        method,
        listing_text: listingText,
      })
      return response.data
    },
  },
})
```

**Commit:** `feat: add listings store with extract action`

---

### Task 10: Integrate Modal into Acquisitions Dashboard

**Goal:** Add "Add from URL" button and wire up modal.

```vue
<!-- In AcquisitionsView.vue, add to EVALUATING column header -->
<template>
  <div class="column evaluating">
    <div class="column-header">
      <h2>Evaluating</h2>
      <button class="add-url-btn" @click="showImportModal = true">
        + Add from URL
      </button>
    </div>
    <!-- ... existing content ... -->
  </div>

  <ImportListingModal
    :is-open="showImportModal"
    @close="showImportModal = false"
    @added="handleListingAdded"
  />
</template>

<script setup>
import { ref } from 'vue'
import ImportListingModal from '@/components/ImportListingModal.vue'

const showImportModal = ref(false)

function handleListingAdded() {
  // Refresh the acquisitions list
  acquisitionsStore.fetchAll()
}
</script>
```

**Commit:** `feat: integrate import modal into acquisitions dashboard`

---

### Task 11: Cleanup Lambda

**Goal:** Create cleanup Lambda for stale items, expired URLs, orphaned images.

**handler.py:**
```python
# cleanup/handler.py
import json
import boto3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Run cleanup tasks."""
    action = event.get("action", "all")

    results = {
        "stale_archived": 0,
        "sources_checked": 0,
        "sources_expired": 0,
        "orphans_deleted": 0,
        "duration_seconds": 0,
    }

    start = datetime.now()

    if action in ("all", "stale"):
        results["stale_archived"] = cleanup_stale_evaluations()

    if action in ("all", "expired"):
        checked, expired = check_expired_sources()
        results["sources_checked"] = checked
        results["sources_expired"] = expired

    if action in ("all", "orphans"):
        results["orphans_deleted"] = cleanup_orphaned_images()

    results["duration_seconds"] = (datetime.now() - start).total_seconds()

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }


def cleanup_stale_evaluations() -> int:
    """Archive items in EVALUATING status > 30 days."""
    # Implementation: query DB, update status to REMOVED
    pass


def check_expired_sources() -> tuple[int, int]:
    """Check source URLs and mark expired ones."""
    # Implementation: HEAD request each URL, update source_expired
    pass


def cleanup_orphaned_images() -> int:
    """Delete S3 images not linked to any book."""
    # Implementation: compare S3 keys with DB, delete orphans
    pass
```

**Commit:** `feat: add cleanup Lambda for maintenance tasks`

---

### Task 12: Admin Cleanup Endpoint

**Goal:** API endpoint to invoke cleanup Lambda.

```python
# backend/app/api/v1/admin.py
@router.post("/cleanup")
def run_cleanup(
    action: str = "all",  # all, stale, expired, orphans
    _user=Depends(require_admin),
):
    """Invoke cleanup Lambda."""
    client = boto3.client("lambda")
    env = os.environ.get("ENVIRONMENT", "staging")

    response = client.invoke(
        FunctionName=f"bluemoxon-{env}-cleanup",
        InvocationType="RequestResponse",
        Payload=json.dumps({"action": action})
    )

    payload = json.loads(response["Payload"].read())
    return json.loads(payload.get("body", "{}"))
```

**Commit:** `feat: add admin cleanup endpoint`

---

### Task 13: Cleanup Admin Panel UI

**Goal:** Add cleanup tools section to dashboard.

```vue
<!-- Add to AcquisitionsView.vue -->
<div class="cleanup-panel" v-if="isAdmin">
  <h3 @click="cleanupExpanded = !cleanupExpanded">
    Cleanup Tools {{ cleanupExpanded ? '▼' : '▶' }}
  </h3>
  <div v-if="cleanupExpanded" class="cleanup-content">
    <div class="cleanup-row">
      <span>Stale evaluations (>30 days): {{ staleCount }} items</span>
      <button @click="runCleanup('stale')">Archive All</button>
    </div>
    <div class="cleanup-row">
      <span>Expired source URLs: {{ expiredCount }} items</span>
      <button @click="runCleanup('expired')">Check All Sources</button>
    </div>
    <div class="cleanup-row">
      <span>Orphaned images: ? files</span>
      <button @click="runCleanup('orphans')">Scan & Cleanup</button>
    </div>
  </div>
</div>
```

**Commit:** `feat: add cleanup admin panel to dashboard`

---

### Task 14: End-to-End Testing & Polish

**Goal:** Manual E2E testing, fix bugs, polish UI.

**Test scenarios:**
1. Happy path: Paste URL → Extract → Preview → Add to Watchlist
2. Mobile URL normalization
3. Rate limit → Retry → Success
4. Alternative method fallback
5. Manual text paste fallback
6. Duplicate detection warning
7. Missing fields handling
8. Image upload on confirm
9. Cleanup panel actions

**Commit:** `test: add E2E test scenarios and polish`

---

## Execution Order

1. ✅ URL utilities (Task 1) - Completed 2025-12-12
2. ✅ Reference matching (Task 2) - Completed 2025-12-12
3. ✅ Bedrock extraction (Task 3) - Completed 2025-12-12
4. ✅ Scraper Lambda infra (Task 4) - Completed 2025-12-12
5. ✅ Scraper invocation service (Task 5) - Completed 2025-12-12
6. ✅ Extract endpoint (Task 6) - Completed 2025-12-12
7. ✅ Database migration (Task 7) - Completed 2025-12-12
8. ✅ Frontend modal (Task 8) - Completed 2025-12-12
9. ✅ Frontend store (Task 9) - Completed 2025-12-12
10. ✅ Dashboard integration (Task 10) - Completed 2025-12-12
11. ⏳ Cleanup Lambda (Task 11) - Deferred (GitHub Issue #189)
12. ⏳ Admin cleanup endpoint (Task 12) - Deferred (GitHub Issue #190)
13. ⏳ Cleanup UI panel (Task 13) - Deferred (GitHub Issue #191)
14. ✅ E2E testing & polish (Task 14) - Completed 2025-12-12

## Estimated Effort

- Tasks 1-3: Backend services (~2-3 hours)
- Tasks 4-6: Scraper + API (~3-4 hours)
- Task 7: Migration (~30 min)
- Tasks 8-10: Frontend (~3-4 hours)
- Tasks 11-13: Cleanup (~2-3 hours)
- Task 14: Testing (~2 hours)

**Total: ~14-18 hours**
