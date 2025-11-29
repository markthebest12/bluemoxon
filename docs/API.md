# BlueMoxon API Documentation

Base URL: `/api/v1`
Authentication: Cognito JWT required on all endpoints

## Books

### List Books
```
GET /books
```
Query parameters:
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20, max: 100)
- `sort_by` (string): Field to sort by (title, author, value_mid, purchase_date)
- `sort_order` (string): asc or desc
- `inventory_type` (string): PRIMARY, EXTENDED, FLAGGED
- `category` (string): Filter by category
- `publisher_id` (int): Filter by publisher
- `binder_id` (int): Filter by binder
- `status` (string): ON_HAND, IN_TRANSIT, SOLD, DONATED
- `binding_authenticated` (bool): Filter authenticated bindings
- `min_value` (decimal): Minimum value_mid
- `max_value` (decimal): Maximum value_mid
- `year_start` (int): Publication year minimum
- `year_end` (int): Publication year maximum

### Get Book
```
GET /books/{id}
```
Returns book with analysis summary and images.

### Create Book
```
POST /books
```
Requires: admin or editor role

### Update Book
```
PUT /books/{id}
```
Requires: admin or editor role

### Delete Book
```
DELETE /books/{id}
```
Requires: admin role

### Update Status
```
PATCH /books/{id}/status
```
Body: `{ "status": "ON_HAND" }`

---

## Search

### Full-Text Search
```
GET /search
```
Query parameters:
- `q` (string): Search query (required)
- `scope` (string): all, books, analyses (default: all)
- `page` (int): Page number
- `per_page` (int): Results per page

---

## Analysis

### Get Analysis
```
GET /books/{id}/analysis
```
Returns parsed analysis with sections.

### Update Analysis
```
PUT /books/{id}/analysis
```
Body: `{ "full_markdown": "..." }`

### Get Raw Markdown
```
GET /books/{id}/analysis/raw
```
Returns raw markdown content.

---

## Images

### List Images
```
GET /books/{id}/images
```

### Get Presigned Upload URL
```
POST /books/{id}/images/presign
```
Body: `{ "filename": "cover.jpg", "content_type": "image/jpeg" }`
Returns: `{ "upload_url": "...", "image_id": "..." }`

### Confirm Upload
```
POST /books/{id}/images/confirm
```
Body: `{ "image_id": "...", "image_type": "cover", "caption": "Front cover" }`

### Delete Image
```
DELETE /books/{id}/images/{img_id}
```

---

## Reference Data

### Publishers
```
GET /publishers
GET /publishers/{id}
```

### Authors
```
GET /authors
GET /authors/{id}
```

### Binders
```
GET /binders
```

### Categories
```
GET /categories
```

---

## Statistics

### Overview
```
GET /stats/overview
```
Returns total items, volumes, and value by inventory type.

### By Category
```
GET /stats/by-category
```

### By Publisher
```
GET /stats/by-publisher
```

### Bindings
```
GET /stats/bindings
```
Returns authenticated binding counts by binder.

---

## Users (Admin Only)

### List Users
```
GET /users
```

### Invite User
```
POST /users/invite
```
Body: `{ "email": "user@example.com", "role": "viewer" }`

### Update Role
```
PATCH /users/{id}/role
```
Body: `{ "role": "editor" }`

### Delete User
```
DELETE /users/{id}
```

---

## Export & Backup

### Export CSV
```
GET /export/csv
```
Query parameters:
- `inventory_type` (string): Filter by type

### Export Search Results
```
GET /export/csv/search
```
Query parameters: Same as /search

### Export Book PDF
```
GET /export/pdf/book/{id}
```
Returns PDF with book details and analysis.

### Export Collection Summary
```
GET /export/pdf/collection
```
Returns PDF summary report.

### Create Backup (Admin)
```
POST /backup/create
```
Triggers full database and image backup.

### List Backups
```
GET /backup/list
```

### Download Backup
```
GET /backup/download/{id}
```
