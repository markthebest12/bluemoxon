# Listing Extraction Design (Phase 5)

## Overview

Extract structured book data from eBay listing URLs using Bedrock Claude. Enables one-click add-to-watchlist from a URL.

## API Endpoint

### `POST /books/parse-listing`

**Request** (either `url` OR `listing_text`):

```json
{
  "url": "https://www.ebay.com/itm/317495720025",
  "listing_text": null
}
```

**Response**:

```json
{
  "source": "ebay",
  "source_item_id": "317495720025",
  "source_url": "https://www.ebay.com/itm/317495720025",
  "title": "The Queen of the Air",
  "author_id": 42,
  "author_name": "John Ruskin",
  "publisher_id": null,
  "publisher_name": "Smith, Elder & Co.",
  "binder_id": 5,
  "binder_name": "Zaehnsdorf",
  "asking_price": 165.00,
  "currency": "USD",
  "publication_date": "1869",
  "volumes": 1,
  "condition_notes": "Minor foxing to preliminaries...",
  "binding_description": "Full crushed morocco by Zaehnsdorf...",
  "image_urls": ["https://i.ebayimg.com/images/g/.../s-l1600.jpg"]
}
```

- `*_id` populated when confident match (>90%), otherwise `null`
- `*_name` always populated for display/search

## Implementation

### Backend Flow

1. **URL Detection**: Parse URL to identify platform (ebay.com, etsy.com)
2. **Content Fetch**: Try HTTP fetch; if blocked/failed, require `listing_text`
3. **Bedrock Extraction**: Send listing HTML/text to Claude for structured extraction
4. **Reference Matching**: Fuzzy match author/publisher/binder against existing records
5. **Return Result**: Structured JSON with IDs where confident

### Bedrock Prompt

```
Extract book listing details as JSON:
- title: Book title only (no author/publisher)
- author: Author name
- publisher: Publisher name
- binder: Bindery name if mentioned
- price: Asking price (number)
- currency: USD/GBP/EUR
- date: Publication date/year
- volumes: Number of volumes (default 1)
- condition: Condition notes
- binding: Binding description

Listing:
{listing_content}
```

### Reference Matching

For author/publisher/binder, fuzzy match against existing records:

- Load all records from DB
- Normalize strings (lowercase, remove punctuation)
- Token-based similarity (Jaccard)
- If similarity >= 0.9, return ID
- Otherwise return name only

## Image Handling

**Approach**: Frontend fetches images (browser not blocked by eBay CORS).

**Flow**:

1. Backend extracts `image_urls` from listing
2. Frontend displays image previews
3. On "Add to Watchlist", frontend fetches image blobs
4. Frontend uploads to presigned S3 URLs
5. Backend associates images with book record

**Presigned URL Endpoint**: `POST /books/{id}/images/presigned`

### Fallback Options (if frontend fetch fails)

**Option A: Playwright in Lambda**

- Add `playwright` to Lambda layer (~50MB)
- Cold start penalty but reliable
- Use for image fetch only

**Option B: Dedicated Image Service**

- Separate container with Playwright
- Invoke via Lambda or direct HTTP
- Better isolation, more infrastructure

## Platform Support

**Phase 5**: eBay only
**Future**: Etsy (same Bedrock extraction, different URL parsing)

Structure code for easy extension:

```python
def parse_listing_url(url: str) -> tuple[str, str]:
    """Return (platform, item_id) from URL."""
    if "ebay.com" in url:
        return ("ebay", extract_ebay_id(url))
    elif "etsy.com" in url:
        return ("etsy", extract_etsy_id(url))
    raise ValueError("Unsupported platform")
```

## Error Handling

| Error | Response |
|-------|----------|
| Invalid URL | 400: "Invalid or unsupported URL" |
| Fetch blocked | 400: "Could not fetch listing. Please paste listing text." |
| Bedrock timeout | 504: "Extraction timed out" |
| Parse failure | 422: "Could not extract listing details" |

## Testing

- Unit tests for URL parsing
- Unit tests for reference matching
- Integration test with mock Bedrock response
- E2E test with real eBay URL (manual/CI skip)
