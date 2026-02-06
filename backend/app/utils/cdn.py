"""CDN URL utilities -- shared between API routes and services."""

from app.config import get_settings

# S3 prefix for book images
S3_IMAGES_PREFIX = "books/"


def get_cloudfront_cdn_url() -> str:
    """Get CloudFront CDN URL from settings or use default.

    Supports two config formats:
    - images_cdn_url: Full URL (e.g., "https://app.bluemoxon.com/book-images")
    - images_cdn_domain: Just the domain (e.g., "d2zwmzka4w6cws.cloudfront.net")
    """
    settings = get_settings()
    if settings.images_cdn_url:
        return settings.images_cdn_url
    if settings.images_cdn_domain:
        return f"https://{settings.images_cdn_domain}"
    return "https://app.bluemoxon.com/book-images"


def get_cloudfront_url(s3_key: str, is_thumbnail: bool = False) -> str:
    """Get the CloudFront CDN URL for an image.

    Args:
        s3_key: The S3 key (filename) of the image
        is_thumbnail: If True, returns the thumbnail URL

    Returns:
        Full CloudFront URL for the image
    """
    if is_thumbnail:
        from app.utils.image_utils import get_thumbnail_key

        s3_key = get_thumbnail_key(s3_key)
    cdn_url = get_cloudfront_cdn_url()
    return f"{cdn_url}/{S3_IMAGES_PREFIX}{s3_key}"
