# BlueMoxon Database Schema

## Overview

PostgreSQL database hosted on Aurora Serverless v2 with full-text search capabilities.

## Tables

### publishers
Tier 1 publishers are pre-seeded (Moxon, Murray, Smith Elder, Macmillan, Chapman & Hall).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Publisher name (unique) |
| tier | VARCHAR(10) | TIER_1, TIER_2, TIER_3, OTHER |
| founded_year | INTEGER | Year founded |
| description | TEXT | Publisher description |

### authors

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(200) | Author name |
| birth_year | INTEGER | Birth year |
| death_year | INTEGER | Death year |
| era | VARCHAR(50) | Victorian, Romantic, etc. |
| first_acquired_date | DATE | When first book by author was acquired |

### binders
Authenticated binding houses (Zaehnsdorf, Rivière, Sangorski, Bayntun).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(50) | Short name (unique) |
| full_name | VARCHAR(200) | Full business name |
| authentication_markers | TEXT | How to identify authentic bindings |

### books
Main entity - represents a single book or set.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| title | VARCHAR(500) | Book title |
| author_id | INTEGER | FK to authors |
| publisher_id | INTEGER | FK to publishers |
| binder_id | INTEGER | FK to binders (nullable) |
| publication_date | VARCHAR(50) | Original format ("1867-1880") |
| year_start | INTEGER | Start year (parsed) |
| year_end | INTEGER | End year (parsed) |
| edition | VARCHAR(100) | Edition info |
| volumes | INTEGER | Number of volumes (default 1) |
| category | VARCHAR(50) | Victorian Poetry, etc. |
| inventory_type | VARCHAR(20) | PRIMARY, EXTENDED, FLAGGED |
| binding_type | VARCHAR(50) | FULL_MOROCCO, HALF_CALF, etc. |
| binding_authenticated | BOOLEAN | Is binding authenticated? |
| binding_description | TEXT | Detailed binding notes |
| condition_grade | VARCHAR(20) | FINE, VERY_GOOD, GOOD, FAIR, POOR |
| condition_notes | TEXT | Condition details |
| value_low | DECIMAL(10,2) | Conservative estimate |
| value_mid | DECIMAL(10,2) | Mid-point estimate |
| value_high | DECIMAL(10,2) | Optimistic estimate |
| purchase_price | DECIMAL(10,2) | Acquisition cost |
| purchase_date | DATE | When acquired |
| purchase_source | VARCHAR(200) | Seller/source |
| discount_pct | DECIMAL(5,2) | Discount from market |
| roi_pct | DECIMAL(5,2) | Return on investment |
| status | VARCHAR(20) | ON_HAND, IN_TRANSIT, SOLD, DONATED |
| notes | TEXT | General notes |
| provenance | TEXT | Ownership history |
| search_vector | TSVECTOR | Full-text search vector |
| created_at | TIMESTAMP | Record creation |
| updated_at | TIMESTAMP | Last update |

### book_analyses
Detailed analysis documents linked to books.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| book_id | INTEGER | FK to books (CASCADE delete) |
| executive_summary | TEXT | Summary section |
| condition_assessment | JSONB | Structured condition data |
| binding_elaborateness_tier | INTEGER | 1-4 tier system |
| market_analysis | JSONB | Comparable sales data |
| historical_significance | TEXT | Historical context |
| recommendations | TEXT | Action items |
| risk_factors | TEXT[] | Array of risks |
| full_markdown | TEXT | Original markdown |
| search_vector | TSVECTOR | Full-text search |
| created_at | TIMESTAMP | Record creation |
| updated_at | TIMESTAMP | Last update |

### book_images
Image metadata (actual images stored in S3).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| book_id | INTEGER | FK to books (CASCADE delete) |
| s3_key | VARCHAR(500) | S3 object key |
| cloudfront_url | VARCHAR(500) | CDN URL |
| image_type | VARCHAR(50) | cover, spine, interior, binding_detail |
| display_order | INTEGER | Sort order |
| is_primary | BOOLEAN | Primary display image |
| caption | TEXT | Image caption |

### users
User preferences (auth handled by Cognito).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| cognito_sub | VARCHAR(100) | Cognito user ID (unique) |
| email | VARCHAR(255) | User email |
| display_name | VARCHAR(100) | Display name |
| role | VARCHAR(20) | admin, editor, viewer |
| preferences | JSONB | User preferences |
| created_at | TIMESTAMP | Record creation |

## Indexes

```sql
-- Full-text search
CREATE INDEX books_search_idx ON books USING GIN(search_vector);
CREATE INDEX analyses_search_idx ON book_analyses USING GIN(search_vector);

-- Common queries
CREATE INDEX books_inventory_type_idx ON books(inventory_type);
CREATE INDEX books_category_idx ON books(category);
CREATE INDEX books_status_idx ON books(status);
CREATE INDEX books_author_idx ON books(author_id);
CREATE INDEX books_publisher_idx ON books(publisher_id);
CREATE INDEX books_binder_idx ON books(binder_id);
```

## Full-Text Search

Search vectors are built from weighted fields:

```sql
-- Books search vector
search_vector =
    setweight(to_tsvector('english', title), 'A') ||
    setweight(to_tsvector('english', coalesce(notes, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(binding_description, '')), 'C');

-- Analysis search vector
search_vector =
    setweight(to_tsvector('english', coalesce(executive_summary, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(full_markdown, '')), 'B');
```

## Migrations

Managed with Alembic. Run migrations:

```bash
cd backend
alembic upgrade head
```

Create new migration:

```bash
alembic revision --autogenerate -m "description"
```
