# eBay Listing Integration Design (Phase 4)

## Overview

Import books from eBay listings with one click. Paste a URL, extract structured data via Bedrock, preview with duplicate detection, and add to watchlist with images preserved.

## User Flow

1. Click "Add from URL" button in EVALUATING column header
2. Modal opens → paste eBay URL → click "Extract"
3. Backend fetches listing via Playwright Lambda, sends to Bedrock for extraction
4. Modal shows preview: title, author, price, binding, image thumbnails
5. If duplicate detected, warning banner: "Similar book exists: [Title] by [Author]"
6. Edit any fields if needed → click "Add to Watchlist"
7. Book created with status=EVALUATING, images uploaded, source_url preserved
8. Modal closes, new card appears in EVALUATING column

## API Endpoint

### `POST /listings/extract`

**Request:**

```json
{
  "url": "https://www.ebay.com/itm/317495720025",
  "method": "playwright",  // or "httpx" for fallback
  "listing_text": null     // for manual paste fallback
}
```

**Response:**

```json
{
  "source": "ebay",
  "source_item_id": "317495720025",
  "source_url": "https://www.ebay.com/itm/317495720025",
  "title": "The Queen of the Air",
  "author_name": "John Ruskin",
  "author_id": 42,
  "publisher_name": "Smith, Elder & Co.",
  "publisher_id": null,
  "binder_name": "Zaehnsdorf",
  "binder_id": 5,
  "asking_price": 165.00,
  "currency": "USD",
  "publication_date": "1869",
  "volumes": 1,
  "condition_notes": "Minor foxing to preliminaries...",
  "binding_description": "Full crushed morocco by Zaehnsdorf...",
  "image_data": [
    { "url": "https://i.ebayimg.com/...", "base64": "...", "content_type": "image/jpeg" }
  ],
  "duplicates": [
    { "id": 203, "title": "Queen of the Air", "author": "Ruskin", "similarity": 0.85 }
  ]
}
```

- `*_id` populated when confident match (>=90% similarity), otherwise `null`
- `*_name` always populated for display/search
- `image_data` includes base64 for S3 upload (CORS prevents frontend fetch)

## URL Normalization

Handle all eBay URL variants:

- `m.ebay.com` → `www.ebay.com`
- `ebay.com` → `www.ebay.com`
- Strip tracking params: `?hash=...`, `&mkcid=...`, `&_trkparms=...`
- Output canonical: `https://www.ebay.com/itm/{item_id}`

```python
def normalize_ebay_url(url: str) -> tuple[str, str]:
    """Return (normalized_url, item_id) from any eBay URL format."""
    # Handle: ebay.com, www.ebay.com, m.ebay.com
    # Extract item ID from /itm/{id} or /itm/{slug}/{id}
    # Strip query params
    # Return canonical URL
```

## Backend Architecture

### Playwright Scraper Lambda

Separate Lambda function: `bluemoxon-{env}-scraper`

**Purpose:** Fetch eBay listing HTML and images server-side (avoids CORS, bot detection)

**Invocation:** Main API Lambda calls via `boto3.client('lambda').invoke()`

**Payload:**

```json
{
  "url": "https://www.ebay.com/itm/317495720025",
  "fetch_images": true
}
```

**Response:**

```json
{
  "html": "<html>...",
  "image_urls": ["https://i.ebayimg.com/..."],
  "images": [
    { "url": "...", "base64": "...", "content_type": "image/jpeg" }
  ]
}
```

**Lambda Configuration:**

- Runtime: Python 3.12
- Memory: 1024 MB (Playwright needs RAM)
- Timeout: 60 seconds
- Layer: playwright-python (~50MB)

### Bedrock Extraction

Use Claude Haiku for fast, cheap structured extraction:

```text
Extract book listing details as JSON. Return ONLY valid JSON, no explanation.

{
  "title": "book title only, no author/publisher in title",
  "author": "author name",
  "publisher": "publisher name if mentioned",
  "binder": "bindery name if mentioned (Rivière, Zaehnsdorf, Bayntun, etc.)",
  "price": 165.00,
  "currency": "USD or GBP or EUR",
  "publication_date": "year or date string",
  "volumes": 1,
  "condition": "condition notes",
  "binding": "binding description"
}

Listing HTML:
{listing_html}
```

### Reference Matching

Fuzzy match extracted names against existing DB records:

```python
def match_reference(name: str, records: list, threshold: float = 0.90) -> int | None:
    """Return record ID if confident match, else None."""
    # Normalize: lowercase, remove "& Son", "Ltd", punctuation
    # Jaccard token similarity
    # Return ID if similarity >= threshold
```

Cache all authors/publishers/binders for 5 minutes to avoid repeated DB queries.

### Duplicate Detection

Query existing books for potential duplicates:

- Same author (by ID or fuzzy name match >= 0.80)
- Title similarity >= 0.80 (reuse `is_duplicate_title()` from scoring service)
- Return top 3 matches with similarity scores

## Error Handling & Fallback Strategy

### Fallback Chain

```text
Attempt 1: Playwright Lambda (headless Chrome)
    ↓ fails
Attempt 2: User clicks "Retry" → Playwright, fresh session, 2s delay
    ↓ fails
Attempt 3: "Try Alternative" → httpx with browser headers, 5s delay
    ↓ fails
Attempt 4: httpx retry, 10s delay
    ↓ fails
Manual paste fallback
```

### Exponential Backoff (Rate Limiting)

| Attempt | Delay | Method |
|---------|-------|--------|
| 1 | 0s | Playwright |
| 2 | 2s | Playwright |
| 3 | 5s | httpx |
| 4 | 10s | httpx |

Max total wait: 30 seconds, then surface manual paste option.

### Error Types & UI Response

| Error | Cause | UI Feedback | Recovery |
|-------|-------|-------------|----------|
| Invalid URL | Not eBay, malformed | Inline error: "Please enter a valid eBay URL" | User fixes URL |
| Listing not found | 404, removed, sold | "Listing not found. It may have been removed." | Try different URL |
| Rate limited | Too many requests | "Rate limited. Retrying in Xs..." with countdown | Auto-retry with backoff |
| Scraper timeout | Playwright hung | "Extraction timed out. Retrying..." | Auto-retry, then alternative |
| Extraction failed | Bedrock couldn't parse | "Couldn't extract details automatically." | Manual paste fallback |
| Partial extraction | Some fields missing | Show preview with empty fields in yellow | User fills manually |

### Manual Paste Fallback

If automated fetching fails:

```text
┌─────────────────────────────────────────────────┐
│  Having trouble fetching this listing.          │
│                                                 │
│  Paste the listing text below:                  │
│  ┌─────────────────────────────────────────┐   │
│  │                                         │   │
│  │                                         │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  [Extract from Text]                            │
│                                                 │
│  Images: [Upload manually after adding]         │
└─────────────────────────────────────────────────┘
```

## Frontend Modal Design

### Component: `ImportListingModal.vue`

**State 1: URL Input**

```text
┌─────────────────────────────────────────────────┐
│  Import from eBay                          [X]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Paste eBay listing URL:                        │
│  ┌─────────────────────────────────────────┐   │
│  │ https://www.ebay.com/itm/...            │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│                              [Extract Listing]  │
└─────────────────────────────────────────────────┘
```

**State 2: Loading**

```text
┌─────────────────────────────────────────────────┐
│  Import from eBay                          [X]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ◐ Fetching listing...                          │
│    ━━━━━━━━━━░░░░░░░░░░                        │
│                                                 │
│                                       [Cancel]  │
└─────────────────────────────────────────────────┘
```

Progress steps: Fetching listing → Extracting details → Checking duplicates

**State 3: Rate Limited**

```text
┌─────────────────────────────────────────────────┐
│  Import from eBay                          [X]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ⏳ Rate limited. Retrying in 8 seconds...      │
│                                                 │
│                                       [Cancel]  │
└─────────────────────────────────────────────────┘
```

**State 4: Error with Options**

```text
┌─────────────────────────────────────────────────┐
│  Import from eBay                          [X]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ⚠️ Couldn't fetch listing                      │
│                                                 │
│  [Retry]  [Try Alternative Method]              │
│                                                 │
│  Or paste listing text manually:                │
│  ┌─────────────────────────────────────────┐   │
│  │                                         │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**State 5: Preview**

```text
┌─────────────────────────────────────────────────────────┐
│  Import from eBay                                  [X]  │
├─────────────────────────────────────────────────────────┤
│ ⚠️ Similar book exists: "Queen of the Air" (85% match)  │
├─────────────────────────────────────────────────────────┤
│  Title:    [The Queen of the Air________________]       │
│  Author:   [John Ruskin______________ ▼] ← dropdown     │
│  Binder:   [Zaehnsdorf_______________ ▼]                │
│  Price:    [£165.00____]  Currency: [GBP ▼]             │
│  Year:     [1869______]   Volumes:  [1__]               │
│  Binding:  [Full crushed morocco, gilt spine...]        │
│                                                         │
│  Images:   [img1] [img2] [img3] [img4]  ← thumbnails    │
│                                                         │
│                      [Cancel]  [Add to Watchlist]       │
└─────────────────────────────────────────────────────────┘
```

**Key UI Elements:**

- Author/Publisher/Binder: Searchable dropdown with matched record pre-selected, "Create new" option
- Missing fields: Yellow border highlight
- Images: Thumbnails, clickable to preview full size
- Duplicate warning: Dismissible banner, links to existing book

## Image Handling

### Flow

```text
Playwright Lambda scrapes eBay
    ↓
Extracts image URLs from listing HTML
    ↓
Downloads images as base64 (server-side, no CORS)
    ↓
Converts WebP → JPEG if needed
    ↓
API returns URLs (preview) + base64 (upload)
    ↓
Frontend shows thumbnails from URLs
    ↓
On "Add to Watchlist": backend uploads base64 to S3
```

### Why Server-Side Download?

- eBay images have CORS restrictions
- Browser can't fetch cross-origin
- Playwright runs server-side, bypasses CORS
- Images captured at scrape time = preserved even if listing removed

### Image Processing

- Convert WebP → JPEG (eBay serves WebP)
- Skip images < 10KB (thumbnails/icons)
- Resize if > 2MB (max 2000px dimension)
- Max 10 images per listing
- First image set as primary

### Fallback

- If image fetch fails: placeholder "Images unavailable"
- User can upload manually after book created
- Not a blocker for adding to watchlist

## Purge & Cleanup

### Cleanup Lambda

Separate Lambda: `bluemoxon-{env}-cleanup`

**Functions:**

- `cleanup_stale_evaluations()` - Archive items in EVALUATING > 30 days
- `check_expired_sources()` - Ping source_urls, mark expired
- `cleanup_orphaned_images()` - Delete S3 images not linked to books

**Invocation:**

- Now: API endpoint `POST /admin/cleanup` → invokes Lambda
- Later: EventBridge scheduled rule (weekly)
- Manual: AWS Console/CLI

**Lambda Configuration:**

- Timeout: 300 seconds (5 min)
- Memory: 512 MB

### Stale Evaluations

Items in EVALUATING status > 30 days:

- Dashboard banner: "5 items have been evaluating for 30+ days"
- Bulk action: "Archive stale items" → status=REMOVED
- Individual "Remove" button per card

### Expired Source URLs

- Ping each `source_url` (HTTP HEAD request)
- Rate limit: max 10 checks/minute
- If 404 or sold: set `source_expired: true` on book
- UI: Show ⚠️ badge on cards with expired sources

### Orphaned Images

- Query S3 for all image keys
- Query DB for all referenced image keys
- Delete S3 objects not in DB
- Run after failed imports or manual deletions

### Admin Cleanup Panel

Collapsible section at bottom of Acquisitions Dashboard:

```text
┌─────────────────────────────────────────────────┐
│  Cleanup Tools                             [▼]  │
├─────────────────────────────────────────────────┤
│  Stale evaluations (>30 days):     5 items      │
│  [Archive All]  [Review List]                   │
│                                                 │
│  Expired source URLs:              3 items      │
│  [Check All Sources]  [View Expired]            │
│                                                 │
│  Orphaned images:                  ? files      │
│  [Scan & Cleanup]                               │
└─────────────────────────────────────────────────┘
```

### Cleanup Response

```json
{
  "stale_archived": 5,
  "sources_checked": 23,
  "sources_expired": 3,
  "orphans_deleted": 12,
  "duration_seconds": 45
}
```

## Database Changes

### New Fields on `books` Table

```sql
ALTER TABLE books ADD COLUMN source_expired BOOLEAN DEFAULT FALSE;
ALTER TABLE books ADD COLUMN listing_fetched_at TIMESTAMP;
```

- `source_expired`: True if source_url returns 404/sold
- `listing_fetched_at`: When listing was originally scraped

### Indexes

```sql
CREATE INDEX books_source_expired_idx ON books(source_expired) WHERE source_expired = TRUE;
CREATE INDEX books_evaluating_created_idx ON books(created_at) WHERE status = 'EVALUATING';
```

## Testing Strategy

### Unit Tests (Backend)

- URL normalization: various eBay URL formats
- URL parsing: extract item ID
- Reference matching: fuzzy match names
- Duplicate detection: title similarity

### Integration Tests (Backend, Mocked External)

- `POST /listings/extract` with mock Playwright response
- Bedrock extraction: mock HTML → structured JSON
- Error scenarios: 404, timeout, rate limit
- Fallback chain: primary fails → alternative triggered

### Integration Tests (Frontend)

- Modal state transitions: input → loading → preview → success
- Error display and retry flow
- Duplicate warning banner
- Form validation

### E2E Tests (Manual)

- Real eBay URL → full flow → book created
- Run manually before releases (avoids rate limits)
- Not in CI

### Test Fixtures

- Save 2-3 real eBay listing HTML samples
- Use for consistent, fast tests

## Infrastructure Changes

### New Lambda Functions

1. **bluemoxon-{env}-scraper**
   - Purpose: Playwright-based eBay scraping
   - Runtime: Python 3.12
   - Memory: 1024 MB
   - Timeout: 60s
   - Layer: playwright-python

2. **bluemoxon-{env}-cleanup**
   - Purpose: Stale/orphan cleanup
   - Runtime: Python 3.12
   - Memory: 512 MB
   - Timeout: 300s

### IAM Permissions

Main API Lambda needs:

```json
{
  "Effect": "Allow",
  "Action": "lambda:InvokeFunction",
  "Resource": [
    "arn:aws:lambda:*:*:function:bluemoxon-*-scraper",
    "arn:aws:lambda:*:*:function:bluemoxon-*-cleanup"
  ]
}
```

### EventBridge Rule (Future)

```hcl
resource "aws_cloudwatch_event_rule" "weekly_cleanup" {
  name                = "bluemoxon-${var.environment}-weekly-cleanup"
  schedule_expression = "cron(0 3 ? * SUN *)"  # Sunday 3am UTC
}
```

## Implementation Order

1. URL normalization & parsing utilities
2. Playwright scraper Lambda
3. Bedrock extraction service
4. Reference matching (author/publisher/binder)
5. Duplicate detection integration
6. `POST /listings/extract` endpoint
7. Frontend modal component
8. Image upload on confirm
9. Cleanup Lambda
10. Admin cleanup panel
11. Testing & polish
