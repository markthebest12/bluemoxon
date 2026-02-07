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
| preferred | BOOLEAN | Preferred entity (+10 scoring bonus) |
| image_url | VARCHAR(500) | Portrait image URL (CDN) |

### authors

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(200) | Author name (unique) |
| birth_year | INTEGER | Birth year |
| death_year | INTEGER | Death year |
| era | VARCHAR(50) | Victorian, Romantic, etc. |
| first_acquired_date | DATE | When first book by author was acquired |
| priority_score | INTEGER | Acquisition priority (default 0) |
| tier | VARCHAR(10) | TIER_1, TIER_2, TIER_3 |
| preferred | BOOLEAN | Preferred entity (+10 scoring bonus) |
| image_url | VARCHAR(500) | Portrait image URL (CDN) |

### binders

Authenticated binding houses (Zaehnsdorf, Rivière, Sangorski, Bayntun).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Short name (unique) |
| full_name | VARCHAR(200) | Full business name |
| authentication_markers | TEXT | How to identify authentic bindings |
| tier | VARCHAR(20) | TIER_1, TIER_2 |
| preferred | BOOLEAN | Preferred entity (+10 scoring bonus) |
| image_url | VARCHAR(500) | Portrait image URL (CDN) |
| founded_year | INTEGER | Year founded |
| closed_year | INTEGER | Year closed (null if still operating) |

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
| status | VARCHAR(20) | EVALUATING, IN_TRANSIT, ON_HAND, SOLD, REMOVED, CANCELED |
| source_url | VARCHAR(500) | Original listing URL |
| source_item_id | VARCHAR(100) | Source item identifier |
| estimated_delivery | DATE | Estimated delivery date |
| tracking_active | BOOLEAN | Whether tracking is actively polling |
| tracking_delivered_at | TIMESTAMP | When package was delivered |
| scoring_snapshot | JSON | Investment scores at acquisition time |
| archive_status | VARCHAR(20) | Wayback archive status (pending, success, failed) |
| source_archived_url | VARCHAR(500) | Wayback Machine URL |
| investment_grade | INTEGER | Computed investment grade (0-100) |
| overall_score | INTEGER | Computed overall score |
| is_first_edition | BOOLEAN | Whether book is a first edition (from analysis) |
| has_provenance | BOOLEAN | Whether provenance is documented |
| provenance_tier | VARCHAR(20) | Provenance quality tier |
| is_complete | BOOLEAN | Whether set has all volumes (default true) |
| acquisition_cost | DECIMAL(10,2) | Total cost including shipping/tax |
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
| risk_factors | JSON | Array of risks |
| full_markdown | TEXT | Original markdown |
| source_filename | VARCHAR(500) | Original filename |
| extraction_status | VARCHAR(20) | success, degraded, failed, null (legacy) |
| model_id | VARCHAR(100) | Bedrock model ID that generated this analysis |
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
| original_filename | VARCHAR(255) | Original upload filename |
| content_hash | VARCHAR(64) | SHA-256 hash for duplicate detection |
| image_type | VARCHAR(50) | cover, spine, interior, binding_detail |
| display_order | INTEGER | Sort order |
| is_primary | BOOLEAN | Primary display image |
| is_background_processed | BOOLEAN | Whether AI background removal was applied |
| caption | TEXT | Image caption |

### users

User accounts (auth handled by Cognito).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| cognito_sub | VARCHAR(100) | Cognito user ID (unique) |
| email | VARCHAR(255) | User email |
| first_name | VARCHAR(100) | User's first name (optional) |
| last_name | VARCHAR(100) | User's last name (optional) |
| role | VARCHAR(20) | admin, editor, viewer |
| created_at | TIMESTAMP | Record creation |

### api_keys

API keys for programmatic access (admin-created).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Key name/description |
| key_hash | VARCHAR(64) | SHA-256 hash of key |
| key_prefix | VARCHAR(8) | First 8 chars for identification |
| created_by_id | INTEGER | FK to users |
| is_active | BOOLEAN | Key active/revoked |
| last_used_at | TIMESTAMP | Last API request |
| created_at | TIMESTAMP | Record creation |

### entity_profiles

AI-generated biographical profiles for authors, publishers, and binders (BMX 3.0).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| entity_type | VARCHAR(20) | author, publisher, binder |
| entity_id | INTEGER | ID of the entity |
| bio_summary | TEXT | AI-generated biographical overview |
| personal_stories | JSONB | Array of biographical facts with year, significance, tone |
| connection_narratives | JSONB | One-sentence connection summaries |
| relationship_stories | JSONB | Extended narratives for significant connections |
| ai_connections | JSONB | Snapshot of AI-discovered connections at generation time |
| model_version | VARCHAR(100) | Bedrock model ID used for generation |
| generated_at | TIMESTAMP | When profile was last generated |
| created_at | TIMESTAMP | Record creation |
| updated_at | TIMESTAMP | Last update |

**Unique constraint:** `(entity_type, entity_id)` -- one profile per entity.

### ai_connections

Canonical storage for AI-discovered personal connections between entities (BMX 3.0).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source_type | VARCHAR(20) | author, publisher, binder |
| source_id | INTEGER | ID of source entity (always lower) |
| target_type | VARCHAR(20) | author, publisher, binder |
| target_id | INTEGER | ID of target entity (always higher) |
| relationship | VARCHAR(20) | family, friendship, influence, collaboration, scandal |
| sub_type | VARCHAR(50) | Specific sub-type (e.g., marriage, mentorship, rivalry) |
| confidence | FLOAT | Confidence score (0.0-1.0) |
| evidence | TEXT | Supporting evidence text |
| created_at | TIMESTAMP | Record creation |
| updated_at | TIMESTAMP | Last update |

**Unique constraint:** `(source_type, source_id, target_type, target_id, relationship)` -- one connection per pair per type.

**Canonical ordering:** Source entity always has the lower ID to prevent duplicate A-B / B-A entries. Upsert uses highest-confidence-wins strategy.

### profile_generation_jobs

Tracks batch entity profile generation jobs (BMX 3.0).

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | Primary key (UUID) |
| status | VARCHAR(20) | pending, in_progress, completed, failed, cancelled |
| owner_id | INTEGER | FK to users.id |
| total_entities | INTEGER | Total entities to process |
| succeeded | INTEGER | Successfully generated count |
| failed | INTEGER | Failed generation count |
| error_log | TEXT | Error details if failed |
| created_at | TIMESTAMP | Job creation |
| updated_at | TIMESTAMP | Last update |
| completed_at | TIMESTAMP | Job completion |

### eval_runbooks

Lightweight evaluation reports for acquisition decisions.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| book_id | INTEGER | FK to books (CASCADE delete, unique) |
| total_score | INTEGER | Composite evaluation score |
| score_breakdown | JSON | Detailed score components |
| recommendation | VARCHAR(20) | PASS or ACQUIRE |
| fmv_low | DECIMAL(10,2) | Fair market value low estimate |
| fmv_high | DECIMAL(10,2) | Fair market value high estimate |
| recommended_price | DECIMAL(10,2) | Suggested offer price |
| condition_grade | VARCHAR(20) | AI-assessed condition grade |
| analysis_narrative | TEXT | Full eval narrative |
| generated_at | TIMESTAMP | When report was generated |
| created_at | TIMESTAMP | Record creation |
| updated_at | TIMESTAMP | Last update |

### notifications

In-app notifications for tracking updates and other events.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| user_id | INTEGER | FK to users (CASCADE delete) |
| book_id | INTEGER | FK to books (SET NULL on delete) |
| message | TEXT | Notification message |
| read | BOOLEAN | Whether notification has been read |
| created_at | TIMESTAMP | Record creation |

### image_processing_jobs

Tracks async AI image processing (background removal) jobs.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| book_id | INTEGER | FK to books (CASCADE delete) |
| source_image_id | INTEGER | FK to book_images (source) |
| processed_image_id | INTEGER | FK to book_images (result) |
| status | VARCHAR(20) | pending, processing, completed, failed |
| attempt_count | INTEGER | Number of processing attempts |
| model_used | VARCHAR(50) | AI model used (u2net, isnet) |
| failure_reason | TEXT | Error details if failed |
| created_at | TIMESTAMP | Job creation |
| completed_at | TIMESTAMP | Job completion |

### app_config

Application configuration key-value store with caching (BMX 3.0).

| Column | Type | Description |
|--------|------|-------------|
| key | VARCHAR(100) | Configuration key (primary key, e.g., model.entity_profiles) |
| value | VARCHAR(500) | Configuration value |
| description | VARCHAR(500) | Human-readable description of the config entry |
| updated_at | TIMESTAMP | Last update |
| updated_by | VARCHAR(100) | Who last changed this value |

**Used for:** AI model assignments per workflow, cached with 5-minute TTL.

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

-- Entity profiles (BMX 3.0)
CREATE UNIQUE INDEX entity_profiles_entity_idx ON entity_profiles(entity_type, entity_id);

-- AI connections (BMX 3.0)
CREATE UNIQUE INDEX ai_connections_pair_idx ON ai_connections(source_type, source_id, target_type, target_id, relationship);
CREATE INDEX ai_connections_source_idx ON ai_connections(source_type, source_id);
CREATE INDEX ai_connections_target_idx ON ai_connections(target_type, target_id);

-- App config (BMX 3.0)
CREATE UNIQUE INDEX app_config_key_idx ON app_config(key);
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
