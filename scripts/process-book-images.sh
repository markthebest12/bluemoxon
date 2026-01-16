#!/bin/bash
# =============================================================================
# Process Book Images - Background Removal with Auto Background Color
# =============================================================================
# Removes backgrounds from book primary images and adds white or black
# background based on the book's brightness.
#
# Usage:
#   ./scripts/process-book-images.sh [OPTIONS] [BOOK_IDS...]
#
# Options:
#   --dry-run       Show what would be done without making changes
#   --all           Process all books with ON_HAND status
#   --threshold N   Brightness threshold (0-255, default 128)
#   --force-white   Force white background for all
#   --force-black   Force black background for all
#   -h, --help      Show this help message
#
# Examples:
#   ./scripts/process-book-images.sh 515 498        # Process specific books
#   ./scripts/process-book-images.sh --all          # Process all ON_HAND books
#   ./scripts/process-book-images.sh --dry-run 515  # Preview without changes
#
# Prerequisites:
#   - Docker (for rembg)
#   - ImageMagick (magick command)
#   - bmx-api CLI configured
# =============================================================================

set -euo pipefail

# Configuration
THRESHOLD=128
DRY_RUN=false
PROCESS_ALL=false
FORCE_BG=""
WORK_DIR="/tmp/book-image-processing"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    head -30 "$0" | grep -E '^#' | tail -n +2 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse arguments
BOOK_IDS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --all)
            PROCESS_ALL=true
            shift
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --force-white)
            FORCE_BG="white"
            shift
            ;;
        --force-black)
            FORCE_BG="black"
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            BOOK_IDS+=("$1")
            shift
            ;;
    esac
done

# Validate
if [ "$PROCESS_ALL" = false ] && [ ${#BOOK_IDS[@]} -eq 0 ]; then
    log_error "No books specified. Use --all or provide book IDs."
    show_help
fi

# Check prerequisites
if ! command -v docker &> /dev/null; then
    log_error "Docker is required but not installed."
    exit 1
fi

if ! command -v magick &> /dev/null; then
    log_error "ImageMagick (magick) is required but not installed."
    exit 1
fi

if ! command -v bmx-api &> /dev/null; then
    log_error "bmx-api is required but not installed."
    exit 1
fi

# Create work directory
mkdir -p "$WORK_DIR"

# Get book IDs if processing all
if [ "$PROCESS_ALL" = true ]; then
    log_info "Fetching all ON_HAND books..."
    BOOK_IDS=($(bmx-api --prod GET '/books?limit=500&status=ON_HAND' 2>/dev/null | jq -r '.items[].id'))
    log_info "Found ${#BOOK_IDS[@]} books to process"
fi

# Process each book
PROCESSED=0
SKIPPED=0
FAILED=0

for BOOK_ID in "${BOOK_IDS[@]}"; do
    echo
    log_info "Processing book $BOOK_ID..."

    # Get book info and primary image
    BOOK_INFO=$(bmx-api --prod GET "/books/$BOOK_ID" 2>/dev/null)
    TITLE=$(echo "$BOOK_INFO" | jq -r '.title // "Unknown"')
    PRIMARY_URL=$(echo "$BOOK_INFO" | jq -r '.primary_image_url // empty')

    if [ -z "$PRIMARY_URL" ]; then
        log_warn "Book $BOOK_ID ($TITLE): No primary image, skipping"
        ((SKIPPED++))
        continue
    fi

    log_info "  Title: $TITLE"
    log_info "  Image: $PRIMARY_URL"

    # Download image
    IMG_EXT="${PRIMARY_URL##*.}"
    ORIG_FILE="$WORK_DIR/${BOOK_ID}_original.${IMG_EXT}"

    if ! curl -sf "$PRIMARY_URL" -o "$ORIG_FILE" 2>/dev/null; then
        log_error "  Failed to download image"
        ((FAILED++))
        continue
    fi

    # Convert to PNG if needed (rembg works better with PNG/JPG)
    if [ "$IMG_EXT" = "webp" ]; then
        PNG_FILE="$WORK_DIR/${BOOK_ID}_original.png"
        if ! magick "$ORIG_FILE" "$PNG_FILE" 2>/dev/null; then
            log_error "  Failed to convert webp to png"
            ((FAILED++))
            continue
        fi
        ORIG_FILE="$PNG_FILE"
    fi

    # Remove background with alpha matting
    NOBG_FILE="$WORK_DIR/${BOOK_ID}_nobg.png"
    log_info "  Removing background..."

    if ! docker run --rm --platform linux/amd64 -v /tmp:/tmp danielgatis/rembg i -a "$ORIG_FILE" "$NOBG_FILE" 2>/dev/null; then
        log_error "  Background removal failed"
        ((FAILED++))
        continue
    fi

    # Calculate brightness
    BRIGHTNESS=$(magick "$NOBG_FILE" -colorspace Gray -format "%[fx:mean*255]" info: 2>/dev/null)
    BRIGHTNESS_INT=${BRIGHTNESS%.*}

    # Determine background color
    if [ -n "$FORCE_BG" ]; then
        BG_COLOR="$FORCE_BG"
    elif [ "$BRIGHTNESS_INT" -lt "$THRESHOLD" ]; then
        BG_COLOR="black"
    else
        BG_COLOR="white"
    fi

    log_info "  Brightness: $BRIGHTNESS_INT (threshold: $THRESHOLD) -> $BG_COLOR background"

    if [ "$DRY_RUN" = true ]; then
        log_info "  [DRY RUN] Would create $BG_COLOR background image and upload"
        ((PROCESSED++))
        continue
    fi

    # Add background
    FINAL_FILE="$WORK_DIR/${BOOK_ID}_final.png"
    if ! magick "$NOBG_FILE" -background "$BG_COLOR" -flatten "$FINAL_FILE" 2>/dev/null; then
        log_error "  Failed to add background"
        ((FAILED++))
        continue
    fi

    # Convert to webp
    WEBP_FILE="$WORK_DIR/${BOOK_ID}_final.webp"
    if ! magick "$FINAL_FILE" -quality 85 "$WEBP_FILE" 2>/dev/null; then
        log_error "  Failed to convert to webp"
        ((FAILED++))
        continue
    fi

    # Upload new image
    log_info "  Uploading new image..."
    UPLOAD_RESULT=$(bmx-api --prod --image "$WEBP_FILE" POST "/books/$BOOK_ID/images" 2>/dev/null)
    NEW_IMAGE_ID=$(echo "$UPLOAD_RESULT" | jq -r '.id // empty')

    if [ -z "$NEW_IMAGE_ID" ]; then
        log_error "  Upload failed"
        ((FAILED++))
        continue
    fi

    log_info "  Uploaded as image ID: $NEW_IMAGE_ID"

    # Get current image order and reorder with new image first
    CURRENT_ORDER=$(bmx-api --prod GET "/books/$BOOK_ID/images" 2>/dev/null | jq -r '[.[].id] | @json')
    NEW_ORDER=$(echo "$CURRENT_ORDER" | jq --argjson new "$NEW_IMAGE_ID" '[$new] + [.[] | select(. != $new)]')

    if ! bmx-api --prod PUT "/books/$BOOK_ID/images/reorder" "$NEW_ORDER" >/dev/null 2>&1; then
        log_warn "  Reorder failed - image uploaded but not set as primary"
    else
        log_success "  Set as primary image"
    fi

    ((PROCESSED++))

    # Cleanup work files for this book
    rm -f "$WORK_DIR/${BOOK_ID}_"* 2>/dev/null || true
done

echo
echo "=============================================="
log_info "Summary:"
log_info "  Processed: $PROCESSED"
log_info "  Skipped:   $SKIPPED"
log_info "  Failed:    $FAILED"
echo "=============================================="
