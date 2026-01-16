# Data Migration Guide

## Overview

BlueMoxon migrates data from the legacy `book-collection` repository:

- `inventory/PRIMARY_COLLECTION.csv` (71 items)
- `inventory/EXTENDED_INVENTORY.csv` (~97 items)
- `inventory/FLAGGED_FOR_REMOVAL.csv` (3 items)
- `documentation/book_analysis/*.md` (~50 files)

## Transition Period Strategy

During development, the `book-collection` repo remains the source of truth. Migration scripts are **idempotent and re-runnable**.

### Sync Command

```bash
# Preview changes (dry run)
python scripts/sync_from_legacy.py --source ~/projects/book-collection --dry-run

# Apply changes
python scripts/sync_from_legacy.py --source ~/projects/book-collection --apply
```

### Change Detection

- **Books:** Matched by `Row` field (PRIMARY) or `Title + Author + Date` composite key
- **Analysis:** Matched by filename pattern
- **Each run:** INSERT new, UPDATE changed, skip unchanged
- **Report:** "5 new books, 3 updated analyses, 12 new images"

## Migration Scripts

### seed_from_csv.py

Seeds the database from book-collection CSV files:

```bash
cd backend
poetry run python ../scripts/seed_from_csv.py
```

This imports:

- `PRIMARY_COLLECTION.csv` → PRIMARY inventory
- `EXTENDED_INVENTORY.csv` → EXTENDED inventory
- Detects authenticated binders from Notes field
- Creates Author, Publisher, Binder records

### import_assets.py

Imports images and analysis documents:

```bash
cd backend
poetry run python ../scripts/import_assets.py
```

This imports:

- Screenshots from `book-collection-assets/screenshots/`
- Analysis markdown from `book-collection/documentation/book_analysis/`

**What it does:**

1. Parses screenshot filenames to match books (e.g., `screenshot-Tennyson_1867_01_cover.jpg`)
2. Copies images to local storage (`/tmp/bluemoxon-images/`)
3. Imports analysis markdown as full_markdown content
4. Extracts executive summary from first paragraph

**Environment variables:**

- `DATABASE_URL` - PostgreSQL connection (default: localhost)
- `LOCAL_IMAGES_PATH` - Where to store images (default: `/tmp/bluemoxon-images`)

### migrate_primary.py

Migrates `PRIMARY_COLLECTION.csv`:

```python
# Handles:
# - Date ranges ("1867-1880" → year_start=1867, year_end=1880)
# - Price parsing ("$385.50" → 385.50)
# - Binding authentication extraction from Notes
# - Author record creation/linking
# - Publisher linking (pre-seeded Tier 1)
# - Search vector generation
```

### migrate_extended.py

Migrates `EXTENDED_INVENTORY.csv`:

- Fewer fields than PRIMARY
- Sets `inventory_type='EXTENDED'`
- Same parsing logic

### migrate_analysis.py

Migrates markdown analysis files:

```python
# Parses sections:
# - Executive Summary
# - Condition Assessment
# - Binding Elaborateness (tier extraction)
# - Market Analysis
# - Historical Significance
# - Recommendations
# - Risk Factors

# Matching logic:
# Filename: "Tennyson_Complete_Works_1867-1880_Moxon_analysis.md"
# → Match to book with title containing "Tennyson" and "Complete Works"
```

## Validation

After migration, verify:

1. **Counts match:**
   - PRIMARY: 71 items
   - EXTENDED: ~97 items
   - FLAGGED: 3 items

2. **Value totals match QUICK_REFERENCE.txt:**
   - Total items: 71 (PRIMARY)
   - Total volumes: 253
   - Total value: ~$37,220

3. **Spot checks:**
   - Search for "Tennyson" returns expected books
   - Analysis documents render correctly
   - Images display properly

## Cutover Checklist

Before going live:

- [ ] All PRIMARY_COLLECTION items migrated and verified
- [ ] All EXTENDED_INVENTORY items migrated
- [ ] All analysis documents rendering correctly
- [ ] All images uploaded to S3
- [ ] Admin can add new books via web UI
- [ ] Search returns expected results
- [ ] Export CSV matches legacy format
- [ ] Announce cutover date to users
- [ ] Final sync from book-collection
- [ ] Archive book-collection repo (read-only)

## Post-Cutover

After BlueMoxon is live:

1. `book-collection` repo becomes read-only archive
2. All new acquisitions added via BlueMoxon web UI
3. CSV export available for backup compatibility
4. Scheduled backups to S3
