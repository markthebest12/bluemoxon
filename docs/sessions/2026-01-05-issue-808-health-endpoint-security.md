# Session: Issue 808 - Health Endpoint Security

**Date**: 2026-01-05
**Issue**: [#808](https://github.com/bluemoxon/bluemoxon/issues/808) - security: Health endpoints run data-mutating operations without authentication

## Problem Summary

`backend/app/api/v1/health.py` exposes multiple POST endpoints that **modify data with no authentication**:

| Endpoint | Risk |
|----------|------|
| `/health/migrate` | Runs DDL/DML SQL statements |
| `/health/cleanup-orphans` | Deletes orphaned records |
| `/health/recalculate-discounts` | Modifies book discount values |
| `/health/merge-binders` | Merges/deletes binder records |

## Session Progress

### Phase 1: Research & Design
- [x] Explore current auth patterns in codebase
- [x] Review health.py endpoints
- [x] Review CI/CD workflow usage
- [x] Design solution with user input (confirmed `require_admin` for all 4)

### Phase 2: Implementation (TDD)
- [x] Write tests for auth requirements (8 tests - 4 unauthenticated, 4 authenticated)
- [x] Add `require_admin` dependency to all 4 endpoints
- [x] Update CI/CD workflow with API key header
- [ ] Validate in staging

---

## Changes Made

### `backend/app/api/v1/health.py`
- Added `from app.auth import require_admin` import
- Added `_user=Depends(require_admin)` to:
  - `cleanup_orphans()` (line 709)
  - `recalculate_discounts()` (line 762)
  - `merge_binders()` (line 812)
  - `run_migrations()` (line 979)

### `backend/app/api/v1/listings.py`
- Added `from app.auth import require_editor` import
- Added `_user=Depends(require_editor)` to:
  - `extract_listing()` - prevents DoS via scraper
  - `extract_listing_async()` - prevents DoS via async scraper

### `backend/app/api/v1/orders.py`
- Added `from app.auth import require_editor` import
- Added `_user=Depends(require_editor)` to:
  - `extract_order()` - prevents DoS via Bedrock LLM

### `backend/tests/test_health.py`
- Added `TestHealthAdminEndpointsSecurity` class with 8 tests
- Tests verify 401 without auth and 200 with admin auth

### `backend/tests/test_listings_api.py`
- Updated `client` fixture to include auth overrides
- Added `unauthenticated_client` fixture
- Added `TestListingsEndpointsSecurity` class with 2 tests

### `backend/tests/test_orders_api.py` (new)
- Security test for orders extract endpoint

### `.github/workflows/deploy.yml`
- Added pre-check step to verify API key secret exists
- Added `BMX_API_KEY` env var with environment-conditional secret
- Added `-H "X-API-Key: ${BMX_API_KEY}"` to migrate curl call

## Required GitHub Secrets

Ensure these secrets exist in GitHub:
- `BMX_API_KEY` - Production API key with admin privileges
- `BMX_STAGING_API_KEY` - Staging API key with admin privileges
