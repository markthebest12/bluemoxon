# API Versioning Strategy Design

**Date:** 2026-01-10
**Issue:** #1003
**Status:** Approved

## Context

From code review of #965 (dashboard charts implementation), adding `by_condition` and `by_category` to `DashboardResponse` raised API compatibility concerns.

## Decision Summary

1. **Audience:** Internal team reference only
2. **Format:** ADR + quick-reference guidelines
3. **Versioning strategy:** Defer v2 mechanics until needed
4. **Compatibility policy:** Moderate (industry standard)

## Compatibility Rules

### Breaking Changes (require version bump)
- Removing a field
- Renaming a field
- Changing a field's type
- Adding a new required field (no default)
- Removing enum values

### Non-Breaking Changes (safe for v1)
- Adding new optional fields (with defaults)
- Adding new enum values
- Adding new endpoints
- Relaxing validation
- Adding query parameters with defaults

## Deliverables

1. `docs/adr/001-api-compatibility-policy.md` - Full ADR with rationale
2. `docs/API_COMPATIBILITY.md` - Quick-reference for daily use
3. Update `backend/app/main.py` - OpenAPI description note

## Implementation

No code changes required - documentation only.
