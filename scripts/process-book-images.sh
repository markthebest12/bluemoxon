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
#   --batch-size N  Number of books to process in parallel (default 4)
#   --threshold N   Brightness threshold (0-255, default 128)
#   --force-white   Force white background for all
#   --force-black   Force black background for all
#   --skip-processed Skip books that already have processed images
#   -h, --help      Show this help message
#
# Examples:
#   ./scripts/process-book-images.sh 515 498        # Process specific books
#   ./scripts/process-book-images.sh --all          # Process all ON_HAND books
#   ./scripts/process-book-images.sh --dry-run --all # Preview without changes
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
BATCH_SIZE=4
SKIP_PROCESSED=false
WORK_DIR="/tmp/book-image-processing"
LOG_DIR="$WORK_DIR/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_batch() { echo -e "${CYAN}[BATCH]${NC} $1"; }

show_help() {
    head -30 "$0" | grep -E '^#' | tail -n +2 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Process a single book - called as background job
process_single_book() {
    local BOOK_ID="$1"
    local THRESHOLD="$2"
    local FORCE_BG="$3"
    local WORK_DIR="$4"
    local LOG_FILE="$LOG_DIR/${BOOK_ID}.log"

    exec > "$LOG_FILE" 2>&1

    echo "START: $(date)"
    echo "Processing book $BOOK_ID..."

    # Get book info and primary image
    BOOK_INFO=$(bmx-api --prod GET "/books/$BOOK_ID" 2>/dev/null)
    TITLE=$(echo "$BOOK_INFO" | jq -r '.title // "Unknown"')
    PRIMARY_URL=$(echo "$BOOK_INFO" | jq -r '.primary_image_url // empty')

    if [ -z "$PRIMARY_URL" ]; then
        echo "SKIP: No primary image"
        echo "END: $(date)"
        exit 0
    fi

    echo "Title: $TITLE"
    echo "Image: $PRIMARY_URL"

    # Download image
    IMG_EXT="${PRIMARY_URL##*.}"
    ORIG_FILE="$WORK_DIR/${BOOK_ID}_original.${IMG_EXT}"

    if ! curl -sf "$PRIMARY_URL" -o "$ORIG_FILE" 2>/dev/null; then
        echo "ERROR: Failed to download image"
        echo "END: $(date)"
        exit 1
    fi

    # Convert to PNG if webp (check if it's actually an image)
    FILE_TYPE=$(file -b "$ORIG_FILE" | cut -d' ' -f1)
    if [ "$FILE_TYPE" = "HTML" ]; then
        echo "ERROR: Downloaded HTML instead of image"
        echo "END: $(date)"
        exit 1
    fi

    if [ "$IMG_EXT" = "webp" ] || [ "$FILE_TYPE" = "RIFF" ]; then
        PNG_FILE="$WORK_DIR/${BOOK_ID}_original.png"
        if ! magick "$ORIG_FILE" "$PNG_FILE" 2>/dev/null; then
            echo "ERROR: Failed to convert to png"
            echo "END: $(date)"
            exit 1
        fi
        ORIG_FILE="$PNG_FILE"
    fi

    # Remove background with alpha matting
    NOBG_FILE="$WORK_DIR/${BOOK_ID}_nobg.png"
    echo "Removing background..."

    if ! docker run --rm --platform linux/amd64 -v /tmp:/tmp danielgatis/rembg i -a "$ORIG_FILE" "$NOBG_FILE" 2>&1; then
        echo "ERROR: Background removal failed"
        echo "END: $(date)"
        exit 1
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

    echo "Brightness: $BRIGHTNESS_INT -> $BG_COLOR background"

    # Add background
    FINAL_FILE="$WORK_DIR/${BOOK_ID}_final.png"
    if ! magick "$NOBG_FILE" -background "$BG_COLOR" -flatten "$FINAL_FILE" 2>/dev/null; then
        echo "ERROR: Failed to add background"
        echo "END: $(date)"
        exit 1
    fi

    # Convert to webp
    WEBP_FILE="$WORK_DIR/${BOOK_ID}_final.webp"
    if ! magick "$FINAL_FILE" -quality 85 "$WEBP_FILE" 2>/dev/null; then
        echo "ERROR: Failed to convert to webp"
        echo "END: $(date)"
        exit 1
    fi

    # Upload new image
    echo "Uploading..."
    UPLOAD_RESULT=$(bmx-api --prod --image "$WEBP_FILE" POST "/books/$BOOK_ID/images" 2>/dev/null)
    NEW_IMAGE_ID=$(echo "$UPLOAD_RESULT" | jq -r '.id // empty')

    if [ -z "$NEW_IMAGE_ID" ]; then
        echo "ERROR: Upload failed"
        echo "END: $(date)"
        exit 1
    fi

    echo "Uploaded as image ID: $NEW_IMAGE_ID"

    # Get current image order and reorder with new image first
    CURRENT_ORDER=$(bmx-api --prod GET "/books/$BOOK_ID/images" 2>/dev/null | jq -r '[.[].id] | @json')
    NEW_ORDER=$(echo "$CURRENT_ORDER" | jq --argjson new "$NEW_IMAGE_ID" '[$new] + [.[] | select(. != $new)]')

    if ! bmx-api --prod PUT "/books/$BOOK_ID/images/reorder" "$NEW_ORDER" >/dev/null 2>&1; then
        echo "WARNING: Reorder failed"
    else
        echo "Set as primary"
    fi

    # Cleanup work files
    rm -f "$WORK_DIR/${BOOK_ID}_"* 2>/dev/null || true

    echo "SUCCESS: $BG_COLOR background"
    echo "END: $(date)"
    exit 0
}

export -f process_single_book
export LOG_DIR

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
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
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
        --skip-processed)
            SKIP_PROCESSED=true
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

# Create work directories
mkdir -p "$WORK_DIR" "$LOG_DIR"

# Get book IDs if processing all
if [ "$PROCESS_ALL" = true ]; then
    log_info "Fetching all ON_HAND books..."
    BOOK_IDS=()
    PAGE=1
    while true; do
        RESPONSE=$(bmx-api --prod GET "/books?page=$PAGE&per_page=100&status=ON_HAND" 2>/dev/null)
        PAGE_IDS=($(echo "$RESPONSE" | jq -r '.items[].id'))
        if [ ${#PAGE_IDS[@]} -eq 0 ]; then
            break
        fi
        BOOK_IDS+=("${PAGE_IDS[@]}")
        TOTAL_PAGES=$(echo "$RESPONSE" | jq -r '.pages')
        if [ "$PAGE" -ge "$TOTAL_PAGES" ]; then
            break
        fi
        ((PAGE++))
    done
    log_info "Found ${#BOOK_IDS[@]} books to process"
fi

# Counters
TOTAL=${#BOOK_IDS[@]}
PROCESSED=0
SKIPPED=0
FAILED=0
BATCH_NUM=0

echo
echo "=============================================="
echo "  Book Image Processing"
echo "  Total: $TOTAL | Batch size: $BATCH_SIZE"
echo "=============================================="
echo

if [ "$DRY_RUN" = true ]; then
    log_warn "DRY RUN MODE - No changes will be made"
    for BOOK_ID in "${BOOK_IDS[@]}"; do
        log_info "Would process book $BOOK_ID"
    done
    exit 0
fi

# Process in batches
for ((i=0; i<TOTAL; i+=BATCH_SIZE)); do
    ((BATCH_NUM++))
    BATCH_END=$((i + BATCH_SIZE))
    if [ $BATCH_END -gt $TOTAL ]; then
        BATCH_END=$TOTAL
    fi

    BATCH_BOOKS=("${BOOK_IDS[@]:i:BATCH_SIZE}")
    BATCH_COUNT=${#BATCH_BOOKS[@]}

    log_batch "========== Batch $BATCH_NUM: Books $((i+1))-$BATCH_END of $TOTAL =========="

    # Start parallel jobs for this batch
    PIDS=()
    for BOOK_ID in "${BATCH_BOOKS[@]}"; do
        log_info "Starting book $BOOK_ID..."
        process_single_book "$BOOK_ID" "$THRESHOLD" "$FORCE_BG" "$WORK_DIR" &
        PIDS+=($!)
    done

    # Wait for all jobs in batch to complete
    log_info "Waiting for batch to complete..."
    for PID in "${PIDS[@]}"; do
        wait $PID 2>/dev/null || true
    done

    # Validate batch results
    log_batch "Validating batch $BATCH_NUM results..."
    BATCH_SUCCESS=0
    BATCH_FAILED=0
    BATCH_SKIPPED=0

    for BOOK_ID in "${BATCH_BOOKS[@]}"; do
        LOG_FILE="$LOG_DIR/${BOOK_ID}.log"
        if [ -f "$LOG_FILE" ]; then
            if grep -q "^SUCCESS:" "$LOG_FILE"; then
                BG_COLOR=$(grep "^SUCCESS:" "$LOG_FILE" | cut -d' ' -f2)
                log_success "  Book $BOOK_ID: $BG_COLOR background"
                ((BATCH_SUCCESS++))
                ((PROCESSED++))
            elif grep -q "^SKIP:" "$LOG_FILE"; then
                REASON=$(grep "^SKIP:" "$LOG_FILE" | cut -d: -f2-)
                log_warn "  Book $BOOK_ID: Skipped -$REASON"
                ((BATCH_SKIPPED++))
                ((SKIPPED++))
            elif grep -q "^ERROR:" "$LOG_FILE"; then
                ERROR=$(grep "^ERROR:" "$LOG_FILE" | head -1 | cut -d: -f2-)
                log_error "  Book $BOOK_ID: Failed -$ERROR"
                ((BATCH_FAILED++))
                ((FAILED++))
            else
                log_error "  Book $BOOK_ID: Unknown status"
                ((BATCH_FAILED++))
                ((FAILED++))
            fi
        else
            log_error "  Book $BOOK_ID: No log file"
            ((BATCH_FAILED++))
            ((FAILED++))
        fi
    done

    log_batch "Batch $BATCH_NUM complete: $BATCH_SUCCESS success, $BATCH_SKIPPED skipped, $BATCH_FAILED failed"

    # Check if too many failures in batch
    if [ $BATCH_FAILED -gt $((BATCH_SIZE / 2)) ]; then
        log_error "More than 50% of batch failed. Stopping to investigate."
        log_error "Check logs in: $LOG_DIR"
        break
    fi

    echo
done

echo
echo "=============================================="
log_info "Final Summary:"
log_info "  Processed: $PROCESSED"
log_info "  Skipped:   $SKIPPED"
log_info "  Failed:    $FAILED"
log_info "  Logs:      $LOG_DIR"
echo "=============================================="
