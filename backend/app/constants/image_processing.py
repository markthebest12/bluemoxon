"""Image processing constants.

Shared between the image processor Lambda and the admin API.
These values control the background removal and thumbnail generation behavior.

IMPORTANT: This is the single source of truth for these constants.
Both lambdas/image_processor/handler.py and app/api/v1/admin.py import from here.
"""

# Background color selection threshold (0-255)
# Images with average brightness below this get black background, above get white
BRIGHTNESS_THRESHOLD = 128

# Maximum processing attempts before marking job as failed
MAX_ATTEMPTS = 3

# Maximum input image dimension (width or height) in pixels
# Images larger than this are rejected to prevent OOM
MAX_IMAGE_DIMENSION = 4096

# Thumbnail settings (matches API endpoint in images.py)
THUMBNAIL_MAX_SIZE = (300, 300)
THUMBNAIL_QUALITY = 85

# Image type priority for source selection (highest priority first)
# Lambda will select best source image based on this order
IMAGE_TYPE_PRIORITY = ["title_page", "binding", "cover", "spine"]

# Attempt number at which to switch from u2net to isnet-general-use model
U2NET_FALLBACK_ATTEMPT = 3

# Minimum output dimension - reject tiny artifacts from rembg
MIN_OUTPUT_DIMENSION = 100
