# BlueMoxon API Documentation

**Version:** 0.1.0
**Base URL:** `/api/v1`
**OpenAPI Spec:** Available at `/openapi.json` (always) and Swagger UI at `/docs` (debug mode)

## Overview

The BlueMoxon API provides comprehensive management of a Victorian book collection, including:
- Book inventory management (PRIMARY, EXTENDED, FLAGGED collections)
- Reference data (Authors, Publishers, Binders)
- Collection statistics and metrics
- Data export (CSV, JSON)
- Full-text search

---

## Books

### List Books
```
GET /books
```

List books with filtering and pagination.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (min: 1) |
| `per_page` | integer | 20 | Items per page (1-100) |
| `inventory_type` | string | - | PRIMARY, EXTENDED, FLAGGED |
| `category` | string | - | Filter by category |
| `status` | string | - | ON_HAND, IN_TRANSIT, SOLD, REMOVED |
| `publisher_id` | integer | - | Filter by publisher |
| `author_id` | integer | - | Filter by author |
| `binder_id` | integer | - | Filter by binder |
| `binding_authenticated` | boolean | - | Filter authenticated bindings |
| `min_value` | number | - | Minimum value_mid |
| `max_value` | number | - | Maximum value_mid |
| `sort_by` | string | title | Field to sort by |
| `sort_order` | string | asc | asc or desc |

**Response:**
```json
{
  "items": [BookResponse],
  "total": 71,
  "page": 1,
  "per_page": 20,
  "pages": 4
}
```

### Get Book
```
GET /books/{book_id}
```

Get a single book by ID with full details.

**Response:** `BookResponse`

### Create Book
```
POST /books
```

Create a new book. Selecting a `binder_id` automatically sets `binding_authenticated: true`.

**Request Body:** `BookCreate`

**Response:** `BookResponse` (201 Created)

### Update Book
```
PUT /books/{book_id}
```

Update an existing book. Changing `binder_id` automatically updates `binding_authenticated`.

**Request Body:** `BookUpdate`

**Response:** `BookResponse`

### Delete Book
```
DELETE /books/{book_id}
```

Delete a book from the collection.

**Response:** 204 No Content

### Update Book Status
```
PATCH /books/{book_id}/status?status={status}
```

Update delivery/inventory status.

**Valid Statuses:** `IN_TRANSIT`, `ON_HAND`, `SOLD`, `REMOVED`

**Response:**
```json
{
  "message": "Status updated",
  "status": "ON_HAND"
}
```

### Update Inventory Type
```
PATCH /books/{book_id}/inventory-type?inventory_type={type}
```

Move book between inventory types.

**Valid Types:** `PRIMARY`, `EXTENDED`, `FLAGGED`

**Response:**
```json
{
  "message": "Inventory type updated",
  "old_type": "PRIMARY",
  "new_type": "FLAGGED"
}
```

### Bulk Update Status
```
POST /books/bulk/status?status={status}
```

Update status for multiple books at once.

**Request Body:**
```json
[1, 2, 3, 4]  // Array of book IDs
```

**Response:**
```json
{
  "message": "Updated 4 books",
  "status": "ON_HAND"
}
```

### Check Duplicate Title
```
GET /books/duplicates/check?title={title}
```

Check if a title already exists (duplicate detection for acquisitions).

**Response:**
```json
{
  "query": "Idylls of the King",
  "matches_found": 2,
  "matches": [
    {
      "id": 1,
      "title": "Idylls of the King",
      "author": "Alfred Lord Tennyson",
      "binder": "Zaehnsdorf",
      "value_mid": 850.0
    }
  ]
}
```

---

## Search

### Full-Text Search
```
GET /search
```

Search across books and analyses.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Search query (min 1 char) |
| `scope` | string | all | all, books, analyses |
| `page` | integer | 1 | Page number |
| `per_page` | integer | 20 | Results per page (1-100) |

---

## Authors

### List Authors
```
GET /authors
```

List all authors, optionally filtered by search.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Filter by name (case-insensitive) |

### Get Author
```
GET /authors/{author_id}
```

Get author details with their books.

### Create Author
```
POST /authors
```

**Request Body:**
```json
{
  "name": "Alfred Lord Tennyson",
  "birth_year": 1809,
  "death_year": 1892,
  "era": "Victorian",
  "first_acquired_date": "2024-01-15"
}
```

### Update Author
```
PUT /authors/{author_id}
```

### Delete Author
```
DELETE /authors/{author_id}
```

Will fail if author has associated books.

---

## Publishers

### List Publishers
```
GET /publishers
```

List all publishers, sorted by tier then name.

### Get Publisher
```
GET /publishers/{publisher_id}
```

Get publisher details with their books.

### Create Publisher
```
POST /publishers
```

**Request Body:**
```json
{
  "name": "Edward Moxon",
  "tier": "TIER_1",
  "founded_year": 1830,
  "description": "Premier Victorian poetry publisher"
}
```

**Tier Values:** `TIER_1`, `TIER_2`, `TIER_3`, `OTHER`

### Update Publisher
```
PUT /publishers/{publisher_id}
```

### Delete Publisher
```
DELETE /publishers/{publisher_id}
```

Will fail if publisher has associated books.

---

## Binders (Authenticated Binding Houses)

### List Binders
```
GET /binders
```

List all premium binding houses.

### Get Binder
```
GET /binders/{binder_id}
```

Get binder details with their books.

### Create Binder
```
POST /binders
```

**Request Body:**
```json
{
  "name": "Zaehnsdorf",
  "full_name": "Zaehnsdorf Ltd.",
  "authentication_markers": "Signed stamp on turn-in, gilt tooling patterns"
}
```

### Update Binder
```
PUT /binders/{binder_id}
```

### Delete Binder
```
DELETE /binders/{binder_id}
```

Will fail if binder has associated books.

---

## Statistics

### Collection Overview
```
GET /stats/overview
```

Get high-level collection statistics.

**Response:**
```json
{
  "primary": {
    "count": 71,
    "volumes": 253,
    "value_low": 28500.0,
    "value_mid": 37220.0,
    "value_high": 45940.0
  },
  "extended": {
    "count": 82
  },
  "flagged": {
    "count": 0
  },
  "total_items": 153,
  "authenticated_bindings": 24,
  "in_transit": 0
}
```

### Collection Metrics
```
GET /stats/metrics
```

Get detailed collection metrics including Victorian %, ROI, and discount averages.

**Response:**
```json
{
  "victorian_percentage": 95.8,
  "average_discount": 75.2,
  "average_roi": 312.5,
  "tier_1_count": 15,
  "tier_1_percentage": 21.1,
  "total_purchase_cost": 8950.0,
  "total_current_value": 37220.0,
  "total_items": 71
}
```

### By Category
```
GET /stats/by-category
```

Get counts and values by category.

### By Publisher
```
GET /stats/by-publisher
```

Get counts and values by publisher with tier info.

### By Author
```
GET /stats/by-author
```

Get counts and values by author.

### By Era
```
GET /stats/by-era
```

Get counts by historical era.

**Response:**
```json
[
  {"era": "Romantic (1800-1837)", "count": 5, "value": 2500.0},
  {"era": "Victorian (1837-1901)", "count": 63, "value": 33000.0},
  {"era": "Edwardian (1901-1910)", "count": 2, "value": 1200.0}
]
```

### Authenticated Bindings
```
GET /stats/bindings
```

Get counts by premium binder.

**Response:**
```json
[
  {"binder": "Zaehnsdorf", "full_name": "Zaehnsdorf Ltd.", "count": 10, "value": 8500.0},
  {"binder": "Rivière", "full_name": "Rivière & Son", "count": 8, "value": 6200.0}
]
```

### Pending Deliveries
```
GET /stats/pending-deliveries
```

Get list of books currently in transit.

**Response:**
```json
{
  "count": 2,
  "items": [
    {
      "id": 65,
      "title": "In Memoriam",
      "author": "Alfred Lord Tennyson",
      "purchase_date": "2025-11-28",
      "value_mid": 230.0
    }
  ]
}
```

---

## Export

### Export to CSV
```
GET /export/csv?inventory_type={type}
```

Export books to CSV format matching PRIMARY_COLLECTION.csv structure.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `inventory_type` | string | PRIMARY | PRIMARY, EXTENDED, FLAGGED |

**Response:** CSV file download

### Export to JSON
```
GET /export/json?inventory_type={type}
```

Export books to JSON format with all details.

**Response:**
```json
{
  "export_date": "2025-11-29T12:00:00",
  "inventory_type": "PRIMARY",
  "total_items": 71,
  "books": [BookExport]
}
```

---

## Schemas

### BookResponse
```json
{
  "id": 1,
  "title": "Idylls of the King",
  "author": {"id": 1, "name": "Alfred Lord Tennyson"},
  "publisher": {"id": 1, "name": "Edward Moxon", "tier": "TIER_1"},
  "binder": {"id": 1, "name": "Zaehnsdorf"},
  "publication_date": "1859-1885",
  "year_start": 1859,
  "year_end": 1885,
  "edition": "First Edition",
  "volumes": 1,
  "category": "Victorian Poetry",
  "inventory_type": "PRIMARY",
  "binding_type": "Full morocco",
  "binding_authenticated": true,
  "binding_description": "Full green morocco with gilt tooling...",
  "condition_grade": "Very Good",
  "condition_notes": "Minor wear to corners",
  "value_low": 700.0,
  "value_mid": 850.0,
  "value_high": 1000.0,
  "purchase_price": 225.0,
  "purchase_date": "2024-11-15",
  "purchase_source": "eBay",
  "discount_pct": 73.5,
  "roi_pct": 278.0,
  "status": "ON_HAND",
  "notes": "Exceptional example",
  "provenance": "Bookplate of Lord X",
  "has_analysis": true,
  "image_count": 5,
  "created_at": "2024-11-15T10:30:00",
  "updated_at": "2024-11-29T12:00:00"
}
```

### BookCreate
```json
{
  "title": "Required",
  "author_id": null,
  "publisher_id": null,
  "binder_id": null,
  "publication_date": "1859",
  "edition": "First Edition",
  "volumes": 1,
  "category": "Victorian Poetry",
  "inventory_type": "PRIMARY",
  "binding_type": "Full morocco",
  "binding_description": "...",
  "condition_grade": "Very Good",
  "condition_notes": "...",
  "value_low": 700.0,
  "value_mid": 850.0,
  "value_high": 1000.0,
  "purchase_price": 225.0,
  "purchase_date": "2024-11-15",
  "purchase_source": "eBay",
  "discount_pct": 73.5,
  "roi_pct": 278.0,
  "status": "ON_HAND",
  "notes": "...",
  "provenance": "..."
}
```

### AuthorResponse
```json
{
  "id": 1,
  "name": "Alfred Lord Tennyson",
  "birth_year": 1809,
  "death_year": 1892,
  "era": "Victorian",
  "first_acquired_date": "2024-01-15",
  "book_count": 8
}
```

### PublisherResponse
```json
{
  "id": 1,
  "name": "Edward Moxon",
  "tier": "TIER_1",
  "founded_year": 1830,
  "description": "Premier Victorian poetry publisher",
  "book_count": 5
}
```

### BinderResponse
```json
{
  "id": 1,
  "name": "Zaehnsdorf",
  "full_name": "Zaehnsdorf Ltd.",
  "authentication_markers": "Signed stamp on turn-in, gilt tooling patterns",
  "book_count": 10
}
```

---

## Health Check

### Health
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid status. Must be one of: IN_TRANSIT, ON_HAND, SOLD, REMOVED"
}
```

### 404 Not Found
```json
{
  "detail": "Book not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
