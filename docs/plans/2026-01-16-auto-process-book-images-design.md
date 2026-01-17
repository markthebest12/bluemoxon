# Design: Auto-Process Book Images During Eval Import

**Issue:** #1136
**Date:** 2026-01-16
**Status:** Draft

## Summary

Automatically process primary book images to remove backgrounds and add contextually appropriate solid backgrounds (black/white based on brightness). Processing happens asynchronously via Lambda when an image becomes primary.

## Architecture

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Image Upload   │────▶│  SQS Queue  │────▶│  Lambda Worker   │
│  (as primary)   │     │  (image-    │     │  (image-         │
│                 │     │  processing)│     │  processor)      │
└─────────────────┘     └─────────────┘     └──────────────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │  rembg (Docker/  │
                                            │  Lambda Layer)   │
                                            └──────────────────┘
```

Follows existing patterns used by AnalysisJob and EvalRunbookJob.

## Trigger Points

Processing is queued when:
1. Image uploaded with `is_primary=True`
2. Existing image reordered to position 1

## Processing Flow

```
1. Receive SQS message (book_id, image_id)
2. Download original image from S3
3. Attempt processing with quality validation
4. On success:
   - Calculate brightness → choose black/white background
   - Upload processed image to S3
   - Create new BookImage record (is_background_processed=True)
   - Reorder: processed=position 1, original→end of carousel
   - Mark job completed
5. On final failure:
   - Keep original as primary
   - Mark job failed with error
```

## Retry Strategy

| Attempt | Model | Notes |
|---------|-------|-------|
| 1 | u2net + alpha matting | Preferred, best edge handling |
| 2 | u2net + alpha matting | Retry same |
| 3 | isnet-general-use | Fallback model |
| Final | Keep original | No processing applied |

## Quality Validation

Both checks must pass after each processing attempt:

| Check | Threshold | Catches |
|-------|-----------|---------|
| Subject area | ≥50% of original image area | Book removed/partially eaten |
| Aspect ratio | Within ±20% of original | Only sliver remained |

Implementation via ImageMagick:
```bash
# Get non-transparent bounding box
magick processed.png -trim info:
# Compare to original dimensions
```

## Database Changes

### New Table: ImageProcessingJob

```python
class ImageProcessingJob(Base):
    id: UUID (PK)
    book_id: FK(Book)
    source_image_id: FK(BookImage)      # original image
    processed_image_id: FK(BookImage)   # result (nullable)
    status: Enum(pending, processing, completed, failed)
    attempt_count: Integer (default 0, max 3)
    model_used: String (nullable)       # "u2net-alpha" or "isnet-general-use"
    failure_reason: String (nullable)   # "area_too_small", "aspect_ratio_mismatch", "processing_error"
    created_at: DateTime
    updated_at: DateTime
    completed_at: DateTime (nullable)
```

### BookImage Addition

```python
is_background_processed: Boolean (default False)
```

## AI Prompt Integration

When `is_background_processed=True` on the primary image, prepend to analysis prompts:

```
Note: This image has had its background digitally removed and replaced
with a solid color. Disregard any edge artifacts, halos, or unnatural
boundaries - focus your analysis on the book itself.
```

### TDD Requirements for Prompts

Before adding the instruction, validate via tests:

```python
def test_prompt_length_within_limits():
    """Current prompts + processed image note stay under thresholds"""

def test_processed_image_note_included_when_flagged():
    """Note added when is_background_processed=True"""

def test_processed_image_note_excluded_when_not_flagged():
    """Note not added when is_background_processed=False"""

def test_prompt_granularity_preserved():
    """All existing prompt sections remain intact with note added"""
```

The added instruction (~180 chars) should be <1% of total prompt length.

## Image Ordering

After successful processing:
- Processed image = position 1 (primary)
- Original image = moved to end of carousel (preserved)

## UI Visibility

None. Status tracked in database only for debugging/queries. If processing fails completely, the original image remains as primary - this is self-evident.

## Infrastructure (Terraform)

New module: `infra/terraform/modules/image-processor/`

- SQS queue: `image-processing-queue`
- Lambda function: `image-processor`
  - Runtime: Python 3.12
  - Memory: 512MB (may need tuning for rembg)
  - Timeout: 5 minutes
  - Container image or layer with rembg dependencies

## File Changes

### New Files
- `backend/models/image_processing_job.py`
- `backend/services/image_processing.py`
- `lambdas/image-processor/handler.py`
- `lambdas/image-processor/requirements.txt`
- `infra/terraform/modules/image-processor/`
- `alembic/versions/xxx_add_image_processing.py`

### Modified Files
- `backend/models/book_image.py` - add `is_background_processed`
- `backend/models/__init__.py` - export new model
- `backend/routers/images.py` - trigger processing on primary
- `backend/prompts/` - add processed image note to relevant prompts

### Test Files
- `backend/tests/test_image_processing.py`
- `backend/tests/test_image_processing_quality.py`
- `backend/tests/test_prompts_with_processed_images.py`

## Acceptance Criteria

- [x] Primary image automatically processed during upload/reorder
- [x] Original image preserved in carousel (at end)
- [x] Processing happens asynchronously (doesn't block upload)
- [x] Failed processing falls back to original gracefully
- [x] Quality validation prevents bad results from being used
- [x] AI prompts updated to note processed images
- [x] Prompt changes validated via TDD

## Open Questions

None - design complete.

## Related

- Existing script: `scripts/process-book-images.sh`
- Docker image: `danielgatis/rembg`
- Brightness threshold: 128 (configurable)
