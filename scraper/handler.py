"""Playwright-based scraper Lambda for eBay listings."""

import io
import json
import logging
import os
import re
import uuid
from pathlib import Path

import boto3
from PIL import Image
from playwright.sync_api import sync_playwright

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Read version from baked-in VERSION file
VERSION_FILE = Path("/app/VERSION")
SCRAPER_VERSION = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "0.0.0-dev"

# Max images per listing (eBay's limit is 24)
MAX_IMAGES = 24

# Min image size to filter out icons/thumbnails
MIN_IMAGE_SIZE = 10000  # 10KB

# Max listings to extract for FMV search
MAX_LISTINGS = 20

# Banner detection thresholds
# Images in the last N positions with wide aspect ratio are likely seller banners
BANNER_ASPECT_RATIO_THRESHOLD = 2.0  # width/height > 2.0 = likely banner
BANNER_POSITION_WINDOW = 3  # Check last N images in carousel


def extract_item_id(url: str, provided_id: str | None = None) -> str:
    """Extract eBay item ID from URL.

    Args:
        url: eBay listing URL
        provided_id: Pre-resolved item ID from the API (preferred if available)

    Returns:
        eBay item ID (12-digit numeric string), or provided_id if given,
        or a random UUID[:8] as last resort fallback
    """
    # Use pre-resolved ID if provided (handles alphanumeric short IDs)
    if provided_id:
        return provided_id

    # Try to extract numeric ID from URL
    match = re.search(r"/itm/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"item=(\d+)", url)
    if match:
        return match.group(1)

    # Last resort fallback - should rarely happen now that API passes item_id
    logger.warning(f"Could not extract numeric item ID from URL: {url}")
    return str(uuid.uuid4())[:8]


def is_likely_banner(image_data: bytes, position: int, total_images: int) -> bool:
    """Detect if image is likely a seller banner based on aspect ratio and position.

    Seller banners (e.g., "Visit My Store!") typically:
    - Appear at the end of the image carousel
    - Have wide aspect ratios (banner-shaped, not book-shaped)

    Args:
        image_data: Raw image bytes
        position: Zero-based index in the image list
        total_images: Total number of images in the listing

    Returns:
        True if image should be filtered out as a likely banner
    """
    # Never filter single-image listings (nothing would remain)
    if total_images <= 1:
        return False

    # Only check images in the last N positions
    if position < total_images - BANNER_POSITION_WINDOW:
        return False

    try:
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        if height <= 0:
            return False
        aspect_ratio = width / height
        is_banner = aspect_ratio > BANNER_ASPECT_RATIO_THRESHOLD
        if is_banner:
            logger.info(
                f"Detected likely banner: position {position}/{total_images}, "
                f"aspect ratio {aspect_ratio:.2f} (threshold: {BANNER_ASPECT_RATIO_THRESHOLD})"
            )
        return is_banner
    except Exception as e:
        logger.warning(f"Could not check banner status: {e}")
        return False  # Fail open - include image if can't read dimensions


# JavaScript to extract listings from eBay search results page
EXTRACT_LISTINGS_JS = """
() => {
    const listings = [];

    // Try multiple selectors for different eBay search result layouts
    // Modern layout uses s-card, older uses s-item
    const cardSelectors = [
        '.s-card',           // Modern search results
        '.srp-results .s-item',  // Older search results
        '[data-viewport]'    // Data-driven results
    ];

    let cards = [];
    for (const sel of cardSelectors) {
        const found = document.querySelectorAll(sel);
        if (found.length > 0) {
            cards = found;
            break;
        }
    }

    cards.forEach(card => {
        try {
            // Extract title - try multiple selectors
            const titleEl = card.querySelector('.s-card__title, .s-item__title, h3');
            const title = titleEl?.textContent?.trim() || '';

            // Skip non-listing cards (ads, placeholders)
            if (!title || title.toLowerCase().includes('shop on ebay')) return;

            // Extract price - look for the bold price element
            const priceEl = card.querySelector('.s-card__price, .s-item__price, [class*="price"]');
            let priceText = priceEl?.textContent?.trim() || '';
            // Extract numeric price
            const priceMatch = priceText.match(/[$£€]([\\d,]+\\.?\\d*)/);
            const price = priceMatch ? parseFloat(priceMatch[1].replace(',', '')) : null;

            // Extract URL
            const linkEl = card.querySelector('a.s-card__link, .s-item__link, a[href*="/itm/"]');
            const url = linkEl?.href || '';

            // Extract condition from subtitle or attribute rows
            const conditionEl = card.querySelector('.s-card__subtitle, .SECONDARY_INFO, [class*="condition"]');
            const condition = conditionEl?.textContent?.trim() || '';

            // Check for SOLD indicator (completed listings)
            const isSold = card.textContent?.toLowerCase().includes('sold') ||
                          card.querySelector('.s-item__purchaseOptions-decorator, .positive')?.textContent?.toLowerCase().includes('sold');

            // Extract sold date if available
            const dateEl = card.querySelector('.s-item__title--tag, .s-card__attribute-row');
            let soldDate = null;
            if (dateEl) {
                const dateText = dateEl.textContent || '';
                // Look for date patterns like "Dec 15" or "Sold Dec 15, 2024"
                const dateMatch = dateText.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2}/i);
                if (dateMatch) {
                    soldDate = dateMatch[0];
                }
            }

            if (title && (price || url)) {
                listings.push({
                    title,
                    price,
                    url,
                    condition,
                    sold_date: soldDate,
                    is_sold: isSold
                });
            }
        } catch (e) {
            // Skip problematic cards
        }
    });

    return listings;
}
"""


def upload_to_s3(bucket: str, key: str, data: bytes, content_type: str) -> bool:
    """Upload image data to S3."""
    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return True
    except Exception as e:
        logger.error(f"S3 upload failed for {key}: {e}")
        return False


def handler(event, context):
    """Scrape eBay listing and upload images to S3.

    Args:
        event: Lambda event with:
            - url: eBay listing URL (required)
            - fetch_images: Whether to download and upload images (default True)

    Returns:
        Lambda response with statusCode and body containing:
            - html: Full page HTML
            - image_urls: List of image URLs found on page
            - s3_keys: List of S3 keys for uploaded images
            - item_id: eBay item ID extracted from URL
    """
    # Handle warmup requests (from CloudWatch scheduled events)
    if event.get("warmup"):
        logger.info(f"Warmup request - keeping Lambda warm (version: {SCRAPER_VERSION})")
        return {"statusCode": 200, "body": json.dumps({"warmup": True, "version": SCRAPER_VERSION})}

    # Handle version check requests
    if event.get("version"):
        return {"statusCode": 200, "body": json.dumps({"version": SCRAPER_VERSION})}

    url = event.get("url")
    fetch_images = event.get("fetch_images", True)
    extract_listings = event.get("extract_listings", False)

    if not url:
        return {"statusCode": 400, "body": json.dumps({"error": "URL required"})}

    # Get S3 bucket from environment
    bucket_name = os.environ.get("IMAGES_BUCKET_NAME")
    if fetch_images and not bucket_name:
        logger.warning("IMAGES_BUCKET_NAME not set, disabling image uploads")
        fetch_images = False

    # Use item_id from API if provided (handles alphanumeric short IDs properly)
    provided_item_id = event.get("item_id")
    item_id = extract_item_id(url, provided_item_id)
    logger.info(f"Processing eBay item {item_id}")

    try:
        with sync_playwright() as p:
            # Lambda-compatible Chromium launch args
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--single-process",
                    "--no-zygote",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                ],
            )
            # Create browser context with realistic settings
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = context.new_page()

            # Set realistic headers
            page.set_extra_http_headers(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"macOS"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1",
                }
            )

            logger.info(f"Navigating to {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for content to load - try multiple selectors
            content_loaded = False
            selectors = [
                ".x-item-title",  # Modern eBay layout
                "#itemTitle",  # Older eBay layout
                "[data-testid='x-item-title']",  # Data attribute fallback
                "h1",  # Last resort - any h1
            ]
            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=15000)
                    content_loaded = True
                    logger.info(f"Content loaded using selector: {selector}")
                    break
                except Exception:
                    continue

            if not content_loaded:
                logger.warning("No title selector found, continuing anyway")

            html = page.content()
            logger.info(f"Got HTML: {len(html)} chars")

            # Check for rate limiting / access denied
            # Use specific patterns to avoid false positives (e.g., "captcha" appears in CSS)
            # Look for actual challenge text, not CSS class names
            rate_limit_patterns = [
                "access denied",
                "blocked by ebay",
                "you've been blocked",
                "please verify you are a human",
                "unusual traffic",
                "complete the captcha",  # Actual captcha challenge text
                "captcha-challenge",  # Actual captcha element
                "security check required",
            ]
            html_lower = html.lower()
            is_rate_limited = any(pattern in html_lower for pattern in rate_limit_patterns)

            if is_rate_limited:
                logger.warning("Rate limiting detected in page content")
                # Skip explicit browser.close() - hangs in Lambda --single-process mode
                return {
                    "statusCode": 429,
                    "body": json.dumps({"error": "Rate limited", "html": html}),
                }

            # Handle extract_listings mode (for FMV search results)
            if extract_listings:
                logger.info("Extracting listings from search results page")
                listings = page.evaluate(EXTRACT_LISTINGS_JS)
                logger.info(f"Extracted {len(listings)} listings from page")

                # Limit to MAX_LISTINGS
                listings = listings[:MAX_LISTINGS]

                # Skip explicit browser.close() - hangs in Lambda --single-process mode
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "listings": listings,
                            "listing_count": len(listings),
                            "html_size": len(html),
                        }
                    ),
                }

            # Extract image URLs
            image_urls = page.evaluate(
                """
                () => {
                    // Try multiple selectors for different eBay layouts
                    const selectors = [
                        '.ux-image-carousel img',
                        '.x-photos img',
                        '.ux-image-grid img',
                        '#icImg',
                        'img[src*="ebayimg.com"]'
                    ];
                    const imgs = new Set();
                    for (const sel of selectors) {
                        document.querySelectorAll(sel).forEach(img => {
                            const src = img.src || img.dataset.src || img.dataset.zoom;
                            if (src && src.includes('ebayimg.com')) {
                                // Get highest resolution version
                                const highRes = src.replace(/s-l\\d+/, 's-l1600');
                                imgs.add(highRes);
                            }
                        });
                    }
                    return Array.from(imgs);
                }
            """
            )
            logger.info(f"Found {len(image_urls)} image URLs")

            # Upload images first, then HTML (so status endpoint knows upload is complete)
            s3_keys = []
            if fetch_images and bucket_name:
                images_to_process = image_urls[:MAX_IMAGES]
                total_images = len(images_to_process)
                for idx, img_url in enumerate(images_to_process):
                    try:
                        response = page.request.get(img_url)
                        if response.ok:
                            body = response.body()
                            content_type = response.headers.get("content-type", "image/jpeg")

                            # Skip small images (likely icons/thumbnails)
                            if len(body) < MIN_IMAGE_SIZE:
                                logger.info(f"Skipping small image ({len(body)} bytes): {img_url}")
                                continue

                            # Skip likely seller banners (wide images at end of carousel)
                            if is_likely_banner(body, idx, total_images):
                                logger.info(f"Skipping suspected seller banner: {img_url}")
                                continue

                            # Determine file extension from content type
                            ext = "jpg"
                            if "webp" in content_type:
                                ext = "webp"
                            elif "png" in content_type:
                                ext = "png"

                            # Upload to S3: listings/{item_id}/image_{idx}.{ext}
                            s3_key = f"listings/{item_id}/image_{idx:02d}.{ext}"
                            if upload_to_s3(bucket_name, s3_key, body, content_type):
                                s3_keys.append(s3_key)
                                logger.info(f"Uploaded image {idx}: {len(body)} bytes -> {s3_key}")
                    except Exception as e:
                        logger.warning(f"Failed to process image {img_url}: {e}")

            # Upload HTML LAST (signals to status endpoint that scraping is complete)
            html_key = f"listings/{item_id}/page.html"
            if bucket_name:
                try:
                    upload_to_s3(bucket_name, html_key, html.encode("utf-8"), "text/html")
                    logger.info(f"Uploaded HTML ({len(html)} chars) -> {html_key}")
                except Exception as e:
                    logger.warning(f"Failed to upload HTML: {e}")

            logger.info(f"Uploaded {len(s3_keys)} images to S3")

            # Skip explicit browser.close() - it hangs indefinitely in Lambda's
            # --single-process mode. Lambda sandbox cleanup handles process termination.
            # All data is already safely uploaded to S3 by this point.

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "html": html,
                        "image_urls": image_urls,
                        "s3_keys": s3_keys,
                        "item_id": item_id,
                    }
                ),
            }

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
