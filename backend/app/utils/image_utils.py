# backend/app/utils/image_utils.py
"""Image format detection utilities using magic numbers.

Provides reliable format detection without depending on file extensions
or S3 metadata. Uses the first 12 bytes of image data to identify format.
"""

from enum import Enum


class ImageFormat(Enum):
    """Supported image formats."""

    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"
    UNKNOWN = "unknown"


# Extension mapping - using .jpg (industry standard, shorter)
EXTENSIONS: dict[ImageFormat, str] = {
    ImageFormat.JPEG: ".jpg",
    ImageFormat.PNG: ".png",
    ImageFormat.WEBP: ".webp",
    ImageFormat.GIF: ".gif",
}

CONTENT_TYPES: dict[ImageFormat, str] = {
    ImageFormat.JPEG: "image/jpeg",
    ImageFormat.PNG: "image/png",
    ImageFormat.WEBP: "image/webp",
    ImageFormat.GIF: "image/gif",
}

MIN_DETECTION_BYTES = 12  # Minimum for WEBP detection (RIFF + WEBP)


def detect_format(data: bytes, strict: bool = False) -> ImageFormat:
    """Detect image format from magic numbers.

    Args:
        data: Image bytes (minimum 12 bytes required)
        strict: If True, raise ValueError on unknown format

    Returns:
        ImageFormat enum value

    Raises:
        ValueError: If data too short or strict=True and format unknown
    """
    if len(data) < MIN_DETECTION_BYTES:
        raise ValueError(f"Insufficient data: need {MIN_DETECTION_BYTES} bytes, got {len(data)}")

    # JPEG: \xff\xd8 (only first 2 bytes matter, third varies by marker type)
    if data[:2] == b"\xff\xd8":
        return ImageFormat.JPEG

    # PNG: 8-byte signature
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ImageFormat.PNG

    # WEBP: RIFF....WEBP (bytes 0-3 and 8-11)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ImageFormat.WEBP

    # GIF: GIF87a or GIF89a
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ImageFormat.GIF

    if strict:
        raise ValueError("Unknown image format")
    return ImageFormat.UNKNOWN


def get_content_type(fmt: ImageFormat) -> str:
    """Return MIME type for format.

    Returns 'application/octet-stream' for UNKNOWN.
    """
    return CONTENT_TYPES.get(fmt, "application/octet-stream")


def get_extension(fmt: ImageFormat) -> str:
    """Return file extension with dot.

    Returns empty string for UNKNOWN.
    """
    return EXTENSIONS.get(fmt, "")


def detect_content_type(data: bytes) -> str:
    """Convenience: detect format and return MIME type directly."""
    return get_content_type(detect_format(data))


def validate_format_match(filename: str, data: bytes) -> bool:
    """Check if filename extension matches actual content.

    Args:
        filename: Filename or path to check
        data: Image bytes (minimum 12 bytes)

    Returns:
        True if extension matches actual format, False otherwise
    """
    actual = detect_format(data)
    if actual == ImageFormat.UNKNOWN:
        return False

    expected_ext = get_extension(actual)
    lower_filename = filename.lower()

    # Special case: both .jpg and .jpeg are valid for JPEG
    if actual == ImageFormat.JPEG and lower_filename.endswith(".jpeg"):
        return True

    return lower_filename.endswith(expected_ext)


def fix_extension(filename: str, data: bytes) -> str:
    """Return filename with correct extension based on actual content.

    Args:
        filename: Filename or path to fix
        data: Image bytes (minimum 12 bytes)

    Returns:
        Filename with correct extension, or unchanged if format unknown
    """
    fmt = detect_format(data)
    if fmt == ImageFormat.UNKNOWN:
        return filename

    # Remove existing extension and add correct one
    if "." in filename:
        base = filename.rsplit(".", 1)[0]
    else:
        base = filename

    return base + get_extension(fmt)
