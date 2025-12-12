"""Playwright-based scraper Lambda for eBay listings."""

import base64
import json
import logging

from playwright.sync_api import sync_playwright

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Scrape eBay listing and return HTML + images.

    Args:
        event: Lambda event with:
            - url: eBay listing URL (required)
            - fetch_images: Whether to download images (default True)

    Returns:
        Lambda response with statusCode and body containing:
            - html: Full page HTML
            - image_urls: List of image URLs found
            - images: List of {url, base64, content_type} for downloaded images
    """
    url = event.get("url")
    fetch_images = event.get("fetch_images", True)

    if not url:
        return {"statusCode": 400, "body": json.dumps({"error": "URL required"})}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Set realistic headers
            page.set_extra_http_headers(
                {
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )

            logger.info(f"Navigating to {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to load
            try:
                page.wait_for_selector(".x-item-title", timeout=10000)
            except Exception:
                # Try alternative selector for older eBay layouts
                page.wait_for_selector("#itemTitle", timeout=5000)

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
                                const highRes = src.replace(/s-l\d+/, 's-l1600');
                                imgs.add(highRes);
                            }
                        });
                    }
                    return Array.from(imgs);
                }
            """
            )
            logger.info(f"Found {len(image_urls)} image URLs")

            images = []
            if fetch_images:
                for img_url in image_urls[:10]:  # Max 10 images
                    try:
                        response = page.request.get(img_url)
                        if response.ok:
                            body = response.body()
                            content_type = response.headers.get("content-type", "image/jpeg")
                            # Skip small images (likely icons/thumbnails)
                            if len(body) > 10000:  # > 10KB
                                images.append(
                                    {
                                        "url": img_url,
                                        "base64": base64.b64encode(body).decode(),
                                        "content_type": content_type,
                                    }
                                )
                                logger.info(f"Downloaded image: {len(body)} bytes")
                    except Exception as e:
                        logger.warning(f"Failed to fetch image {img_url}: {e}")

            browser.close()
            logger.info(f"Returning {len(images)} images")

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"html": html, "image_urls": image_urls, "images": images}
                ),
            }

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
