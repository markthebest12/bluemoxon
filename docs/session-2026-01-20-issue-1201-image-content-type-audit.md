# Session Log: Issue #1201 - Image Content-Type Audit

**Date**: 2026-01-20
**Issue**: [#1201](https://github.com/markthebest12/bluemoxon/issues/1201) - Comprehensive audit: Image format and Content-Type mismatches across codebase

## Summary

This issue consolidates all JPEG/JPG/PNG/WebP content-type and extension mismatches across the BlueMoxon codebase. These issues can cause:
- CloudFront caching incorrect Content-Type headers
- Browser download dialogs showing wrong extensions
- Image processing libraries failing on format mismatches
- Inconsistent behavior across different image handling paths

## Affected Files

| File | Issue |
|------|-------|
| `backend/lambdas/image_processor/handler.py` | Thumbnail JPEG saved with .png extension |
| `backend/app/api/v1/images.py:447` | Hardcoded JPEG for all uploads |
| `backend/app/api/v1/images.py:129-140` | Extension preservation acknowledged |
| `backend/app/api/v1/books.py:341` | Hardcoded JPEG for copied images |
| `backend/app/services/bedrock.py:321-333` | Fallback logic for unreliable ContentType |

## Recommended Fix Approach

### Phase 1: Stop Creating New Mismatches
1. Image upload: Detect actual image format and set correct Content-Type
2. Thumbnail generation: Use `.jpg` extension when saving as JPEG
3. Image processor Lambda: Generate thumbnail key with `.jpg` extension

### Phase 2: Migration for Existing Data
1. Audit: Query S3 for objects with mismatched extension/Content-Type
2. Document: Count affected objects by category
3. Migrate: Rename S3 objects and update database records
4. Cleanup: Update CloudFront invalidations if needed

### Phase 3: Consolidation
1. Create centralized image utilities module with:
   - `detect_image_format(bytes)` - Magic number detection
   - `get_content_type(format)` - Consistent MIME types
   - `get_extension(format)` - Consistent extensions
2. Replace all hardcoded Content-Types with utility calls

## Progress

- [x] Brainstorming/Design phase
- [x] Implementation plan created
- [x] Phase 1 implementation (code fixes)
- [x] Phase 2 implementation (migration endpoint)
- [x] Phase 3 implementation (get_thumbnail_key update)
- [ ] PR to staging
- [ ] Staging validation
- [ ] Run migrations
- [ ] PR to production

## Session Notes

### 2026-01-20 - Design Complete

**Design decisions made**:
1. New `image_utils.py` module at `backend/app/utils/image_utils.py`
2. Magic number detection (first 12 bytes) - no Pillow dependency
3. Extension standardization: always `.jpg` for JPEG (industry standard)
4. True zero-downtime migration via pre-migration approach:
   - Deploy migration endpoint
   - Run Stage 2 (create .jpg copies)
   - Deploy updated `get_thumbnail_key()`
   - Run Stage 1 and Stage 3
5. Admin endpoint with background job execution
6. Range requests for S3 (99.99% bandwidth savings)
7. Batch deletes in Stage 3 for efficiency

**Design document**: `docs/plans/2026-01-20-image-content-type-audit-design.md`

### 2026-01-20 - Implementation Complete

**Parallel execution with git worktrees:**
- Group A (parallel): Task 1 (image_utils), Task 5 (migration schemas)
- Group B (parallel): Task 2 (images.py), Task 3 (books.py), Task 4 (bedrock.py)
- Group C (parallel): Task 6 (migration service), Task 7 (migration API)
- Group D: Task 8 (get_thumbnail_key update)

**Files created:**
- `backend/app/utils/image_utils.py` - Format detection utilities (35 tests)
- `backend/app/schemas/migration.py` - Pydantic models for migration
- `backend/app/services/image_migration.py` - 3-stage migration service
- `backend/tests/utils/test_image_utils.py` - Unit tests
- `backend/tests/services/test_image_migration.py` - Migration tests

**Files modified:**
- `backend/app/api/v1/images.py` - Format detection on upload, get_thumbnail_key → .jpg
- `backend/app/api/v1/books.py` - MetadataDirective=COPY in copy_object
- `backend/app/services/bedrock.py` - Use image_utils for format detection
- `backend/app/api/v1/admin.py` - Migration endpoints
- `backend/app/services/image_cleanup.py` - get_thumbnail_key → .jpg

**All tests passing:** 38 new tests + existing tests

**Deployment order (IMPORTANT):**
1. Deploy Tasks 1-7 (migration endpoint + code fixes)
2. Run Stage 2 migration: `POST /admin/migrate-image-formats {"stage": 2, "dry_run": false}`
3. Deploy Task 8 (get_thumbnail_key update)
4. Run Stage 1 migration (fix ContentType)
5. Run Stage 3 cleanup (delete old .png thumbnails)

**Next**: Create PR to staging for review.
