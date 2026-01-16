# Session: Condition Grade Dropdown with Descriptions

**Date**: 2026-01-07
**Issue**: #923
**Goal**: Convert condition_grade from free-form text to dropdown with human-readable labels and subtitle descriptions

## Context

- Currently `condition_grade` is a text input expecting enum values (FINE, VERY_GOOD, GOOD, FAIR, POOR)
- Legacy data may have "Good" instead of "GOOD", causing validation errors
- Error messages were improved to be human-readable (earlier in this session)

## Requirements

- Dropdown with human-readable labels (e.g., "Very Good" displays, "VERY_GOOD" stored)
- Subtitle descriptions under each option explaining criteria
- Mobile-friendly (no hover-dependent tooltips)

## Progress

- [x] Brainstorm design approach (AB Bookman's standard)
- [x] Design doc written: `docs/plans/2026-01-07-condition-grade-dropdown-design.md`
- [x] Backend: Added NEAR_FINE to ConditionGrade enum
- [x] Backend: Created migration `m0001_normalize_condition_grade.py`
- [x] Frontend: Created `SelectWithDescriptions.vue` component
- [x] Frontend: Added CONDITION_GRADE_OPTIONS to constants
- [x] Frontend: Updated BookForm.vue to use new component
- [x] All linting/type-check/formatting passes
- [x] PR #924 created for staging review
- [ ] Review and merge to staging
- [ ] Test in staging
- [ ] PR to production

## Files Changed

- `backend/app/enums.py` - Added NEAR_FINE
- `backend/alembic/versions/m0001_normalize_condition_grade.py` - Migration
- `frontend/src/components/SelectWithDescriptions.vue` - New component
- `frontend/src/constants/index.ts` - Added grade options
- `frontend/src/components/books/BookForm.vue` - Uses new dropdown
