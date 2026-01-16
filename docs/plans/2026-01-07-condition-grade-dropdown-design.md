# Condition Grade Dropdown Design

**Issue**: #923
**Date**: 2026-01-07

## Overview

Convert `condition_grade` from free-form text to a dropdown with human-readable labels and descriptions, following AB Bookman's Weekly grading standards.

## Grading Scale (AB Bookman's)

| Enum Value | Label | Description |
|------------|-------|-------------|
| FINE | Fine | Nearly as new, no defects |
| NEAR_FINE | Near Fine | Approaching fine, very minor defects |
| VERY_GOOD | Very Good | Worn but untorn, minimum for collectors |
| GOOD | Good | Average used, regular wear |
| FAIR | Fair | Wear and tear, but complete |
| POOR | Poor | Heavily damaged, reading copy only |

## Legacy Value Mapping

| Analysis/Legacy Value | → Enum |
|----------------------|--------|
| Fine, F | FINE |
| Near Fine, NF, VG+ | NEAR_FINE |
| Very Good, VG | VERY_GOOD |
| VG-, Good+, Good, G | GOOD |
| Fair | FAIR |
| Poor | POOR |

## Components

### 1. Backend Changes

**`backend/app/enums.py`** - Add NEAR_FINE:

```python
class ConditionGrade(StrEnum):
    FINE = "FINE"
    NEAR_FINE = "NEAR_FINE"  # NEW
    VERY_GOOD = "VERY_GOOD"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
```

### 2. Database Migration

One-time Alembic migration to normalize existing data:

1. Map known legacy values to enum values
2. For NULL/unmapped, pull from `book_analyses.condition_assessment->>'condition_grade'`
3. Log unmapped values for manual review

### 3. Frontend Component

**`frontend/src/components/SelectWithDescriptions.vue`** - Reusable dropdown:

- Props: `modelValue`, `options: {value, label, description}[]`, `placeholder`, `disabled`
- Custom dropdown (not native select) to support two-line options
- Description text smaller (`text-xs text-gray-500`)
- Matches existing `.input` styling

### 4. Frontend Constants

**`frontend/src/constants/index.ts`**:

```typescript
export const CONDITION_GRADE_OPTIONS = [
  { value: "FINE", label: "Fine", description: "Nearly as new, no defects" },
  { value: "NEAR_FINE", label: "Near Fine", description: "Approaching fine, very minor defects" },
  { value: "VERY_GOOD", label: "Very Good", description: "Worn but untorn, minimum for collectors" },
  { value: "GOOD", label: "Good", description: "Average used, regular wear" },
  { value: "FAIR", label: "Fair", description: "Wear and tear, but complete" },
  { value: "POOR", label: "Poor", description: "Heavily damaged, reading copy only" },
] as const;
```

### 5. BookForm.vue Update

Replace text input with SelectWithDescriptions component.

## Implementation Order

These can run in parallel:

- **Stream A**: Backend enum + migration
- **Stream B**: Frontend component + constants + BookForm update

## Testing

- Backend: Test migration maps values correctly
- Frontend: Component unit tests, BookForm integration
