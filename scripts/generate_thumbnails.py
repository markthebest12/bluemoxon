#!/usr/bin/env python3
"""Generate thumbnails for all existing images that don't have them."""

import os
from pathlib import Path

from PIL import Image

# Thumbnail settings (match backend/app/api/v1/images.py)
THUMBNAIL_SIZE = (300, 300)
THUMBNAIL_QUALITY = 85

# Local images storage
LOCAL_IMAGES_PATH = Path(os.environ.get("LOCAL_IMAGES_PATH", "/tmp/bluemoxon-images"))

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def generate_thumbnail(source_path: Path, thumbnail_path: Path) -> bool:
    """Generate a thumbnail from source image.

    Args:
        source_path: Path to the original image
        thumbnail_path: Path where thumbnail should be saved

    Returns:
        True if thumbnail was generated successfully, False otherwise
    """
    try:
        with Image.open(source_path) as img:
            # Convert RGBA/P mode to RGB for JPEG output
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # Use LANCZOS for high-quality downsampling
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, "JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            return True
    except Exception as e:
        print(f"  ERROR: Failed to generate thumbnail for {source_path.name}: {e}")
        return False


def get_thumbnail_path(image_path: Path) -> Path:
    """Get the thumbnail path for an image."""
    # Thumbnail is thumb_{basename}.jpg (always JPEG)
    thumb_name = f"thumb_{image_path.stem}.jpg"
    return image_path.parent / thumb_name


def main():
    """Generate thumbnails for all images missing them."""
    if not LOCAL_IMAGES_PATH.exists():
        print(f"ERROR: Images path not found: {LOCAL_IMAGES_PATH}")
        return

    print(f"Scanning {LOCAL_IMAGES_PATH} for images...")

    # Find all images
    images = []
    for ext in IMAGE_EXTENSIONS:
        images.extend(LOCAL_IMAGES_PATH.glob(f"*{ext}"))
        images.extend(LOCAL_IMAGES_PATH.glob(f"*{ext.upper()}"))

    # Filter out thumbnails and tiny placeholder files
    images = [
        img for img in images
        if not img.name.startswith("thumb_") and img.stat().st_size > 1000
    ]

    print(f"Found {len(images)} images")

    generated = 0
    skipped = 0
    failed = 0

    for img_path in sorted(images):
        thumb_path = get_thumbnail_path(img_path)

        if thumb_path.exists():
            skipped += 1
            continue

        print(f"  Generating: {thumb_path.name}")
        if generate_thumbnail(img_path, thumb_path):
            generated += 1
        else:
            failed += 1

    print(f"\n=== Summary ===")
    print(f"  Generated: {generated}")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total thumbnails: {generated + skipped}")


if __name__ == "__main__":
    main()
