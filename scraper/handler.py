"""Playwright-based scraper Lambda for eBay listings."""

import json
import logging
import os
import re
import uuid

import boto3
from playwright.sync_api import sync_playwright

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Max images per listing (eBay's limit is 24)
MAX_IMAGES = 24

# Min image size to filter out icons/thumbnails
MIN_IMAGE_SIZE = 10000  # 10KB


def extract_item_id(url: str) -> str:
    """Extract eBay item ID from URL."""
    match = re.search(r"/itm/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"item=(\d+)", url)
    if match:
        return match.group(1)
    return str(uuid.uuid4())[:8]


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
        logger.info("Warmup request - keeping Lambda warm")
        return {"statusCode": 200, "body": json.dumps({"warmup": True})}

    url = event.get("url")
    fetch_images = event.get("fetch_images", True)

    if not url:
        return {"statusCode": 400, "body": json.dumps({"error": "URL required"})}

    # Get S3 bucket from environment
    bucket_name = os.environ.get("IMAGES_BUCKET_NAME")
    if fetch_images and not bucket_name:
        logger.warning("IMAGES_BUCKET_NAME not set, disabling image uploads")
        fetch_images = False

    item_id = extract_item_id(url)
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
            page = browser.new_page()

            # Set realistic headers
            page.set_extra_http_headers(
                {
                    "Accept-Language": "en-US,en;q=0.9",
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
            if "Access Denied" in html or "blocked" in html.lower():
                browser.close()
                return {
                    "statusCode": 429,
                    "body": json.dumps({"error": "Rate limited", "html": html}),
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

            s3_keys = []
            if fetch_images and bucket_name:
                for idx, img_url in enumerate(image_urls[:MAX_IMAGES]):
                    try:
                        response = page.request.get(img_url)
                        if response.ok:
                            body = response.body()
                            content_type = response.headers.get(
                                "content-type", "image/jpeg"
                            )

                            # Skip small images (likely icons/thumbnails)
                            if len(body) < MIN_IMAGE_SIZE:
                                logger.info(
                                    f"Skipping small image ({len(body)} bytes): {img_url}"
                                )
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
                                logger.info(
                                    f"Uploaded image {idx}: {len(body)} bytes -> {s3_key}"
                                )
                    except Exception as e:
                        logger.warning(f"Failed to process image {img_url}: {e}")

            logger.info(f"Closing browser...")
            page.close()
            browser.close()
            logger.info(f"Uploaded {len(s3_keys)} images to S3")

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
