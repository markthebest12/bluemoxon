# Dedicated Garbage Image Detection Design

**Issue:** #748
**Date:** 2026-01-01
**Status:** Ready for implementation

## Problem

Book 539 contains 5 garbage images that weren't filtered despite eval runbook running:

- Image 19: Yarn/textile skeins (not a book)
- Image 20: Decorative buttons (not a book)
- Image 21: "From Friend to Friend" - different book
- Image 22: "With Kennedy" by Pierre Salinger - different book
- Image 23: German-English Dictionary - different book

**Root cause:** Prompt overload - garbage detection buried in condition-focused prompt.

## Solution

Dedicated garbage detection step before eval runbook generation with inverted prompt logic.

## Architecture & Flow

```text
Scrape/Extract → [NEW: Garbage Detection] → Eval Runbook → Analysis
```

New function `detect_garbage_images()` runs before `generate_eval_runbook()`.

**Flow:**

1. Fetch book's current images from DB
2. Get listing title + author
3. Call Claude Sonnet with all images + title/author
4. For each image, Claude answers: "Does this show the book '{title}' by {author}?"
5. Images marked "no" passed to existing `delete_unrelated_images()`
6. Remaining images proceed to eval runbook generation

**Integration point:** In `books.py`, after stale job check, before eval runbook generation.

## Prompt Design

Inverted logic - ask "is this THE book?" instead of "is this garbage?"

```text
You are examining images from an online book listing.

The listing is for: "{title}" by {author}

For each image, determine if it shows THIS SPECIFIC BOOK.

Answer YES if the image shows:
- The cover of "{title}" by {author}
- Interior pages of this book
- The spine showing this title
- Multiple angles of this specific book

Answer NO if the image shows:
- A completely different book (different title or author)
- Objects that are not books (yarn, buttons, clothing, etc.)
- Seller promotional material or store banners
- Generic stock photos
- Shipping/contact information graphics

Return a JSON array of image indices (0-based) that should be REMOVED.
Example: [3, 7, 12] means images 3, 7, and 12 are NOT this book.
Return [] if all images show the correct book.
```

**Response format:**

```json
{"garbage_indices": [19, 20, 21, 22, 23]}
```

## Implementation

**New function in `eval_generation.py`:**

```python
async def detect_garbage_images(
    book_id: int,
    images: list[BookImage],
    title: str,
    author: str | None,
    db: AsyncSession,
) -> list[int]:
    """
    Detect and remove images that don't show the specified book.
    Returns indices of removed images.
    """
```

**Call site in `books.py`:**

```python
garbage_indices = await detect_garbage_images(
    book_id=book.id,
    images=book.images,
    title=book.title or listing.title,
    author=book.author,
    db=db,
)
if garbage_indices:
    logger.info(f"Removed {len(garbage_indices)} garbage images from book {book.id}")
```

**Error handling:** If detection fails, log warning and proceed (non-blocking).

## Testing Strategy

**Unit tests (`test_eval_generation.py`):**

1. Happy path - returns garbage indices for mixed images
2. All valid - returns empty array when all images match
3. All garbage - handles edge case
4. Missing author - works with title-only
5. Claude failure - returns empty array, logs warning

**Integration test:**

- Use book 539's listing (`listings/397448193086/`)
- Verify images 19-23 detected as garbage
- Verify images 0-18 retained

## Observability

```python
logger.info(f"Starting garbage detection for book {book_id} ({len(images)} images)")
logger.info(f"Garbage detection found {len(indices)} unrelated images: {indices}")
logger.warning(f"Garbage detection failed for book {book_id}: {error}")
```

## Decisions Summary

| Decision | Choice |
|----------|--------|
| Scope | Garbage detection only, S3 prompts separate (#747) |
| When | Before eval runbook generation |
| Orphan handling | Delete immediately via existing function |
| Prompt strategy | Inverted logic: "Is this THE book?" |
| Model | Sonnet |
| Context | Title + Author |
| Error handling | Log and proceed (non-blocking) |

## Related

- S3 prompt infrastructure: #747 (future)
- Parent issue: #743 (Napoleon improvements)
