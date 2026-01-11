# Book Metadata Display Improvements

**Issue:** #1060
**Date:** 2026-01-11
**Status:** Design approved

## Problem

The Publication Details section in `BookMetadataSection.vue` displays raw database values instead of human-readable text:

1. **Condition** shows `NEAR_FINE` instead of "Near Fine" with description
2. **Publisher tier** shows `TIER_2` instead of "Tier 2"
3. **Status dropdown** is too narrow, arrow overlaps text

## Design Decisions

| Item | Decision |
|------|----------|
| Condition | Show label + description (matches edit mode) |
| Publisher tier | Add to constants for consistency |
| Status dropdown | Add `min-w-[120px]` for proper sizing |

## Implementation

### 1. Constants Updates

**File:** `frontend/src/constants/index.ts`

Add publisher tier options following existing pattern:

```typescript
export const PUBLISHER_TIERS = {
  TIER_1: "TIER_1",
  TIER_2: "TIER_2",
  TIER_3: "TIER_3",
  TIER_4: "TIER_4",
} as const;

export type PublisherTier = (typeof PUBLISHER_TIERS)[keyof typeof PUBLISHER_TIERS];

export const PUBLISHER_TIER_OPTIONS = [
  { value: "TIER_1", label: "Tier 1" },
  { value: "TIER_2", label: "Tier 2" },
  { value: "TIER_3", label: "Tier 3" },
  { value: "TIER_4", label: "Tier 4" },
] as const;
```

### 2. Component Changes

**File:** `frontend/src/components/book-detail/BookMetadataSection.vue`

**New imports:**
```typescript
import { CONDITION_GRADE_OPTIONS, PUBLISHER_TIER_OPTIONS } from "@/constants";
```

**New helper functions:**
```typescript
function getConditionDisplay(grade: string | null) {
  if (!grade) return null;
  const option = CONDITION_GRADE_OPTIONS.find((c) => c.value === grade);
  return option || { label: grade, description: "" };
}

function getTierLabel(tier: string | null): string {
  if (!tier) return "";
  const option = PUBLISHER_TIER_OPTIONS.find((t) => t.value === tier);
  return option ? option.label : tier.replace("_", " ");
}
```

**Template changes:**

1. **Condition display** - Replace raw value with label + description:
```html
<dt class="text-sm text-gray-500">Condition</dt>
<dd>
  <template v-if="getConditionDisplay(book.condition_grade)">
    <span class="font-medium">{{ getConditionDisplay(book.condition_grade)?.label }}</span>
    <p class="text-xs text-gray-500">{{ getConditionDisplay(book.condition_grade)?.description }}</p>
  </template>
  <span v-else>-</span>
</dd>
```

2. **Publisher tier** - Use helper function:
```html
({{ getTierLabel(book.publisher.tier) }})
```

3. **Status dropdown** - Add minimum width and increase padding:
```html
'min-w-[120px] px-3 py-1.5 rounded-sm text-sm font-medium...'
```

### 3. Testing

**File:** `frontend/src/components/book-detail/__tests__/BookMetadataSection.spec.ts`

Add tests for:
- Condition shows human-readable label instead of DB value
- Condition shows description underneath label
- Condition shows dash when null
- Publisher tier formats `TIER_2` as "Tier 2"
- Status dropdown has sufficient width

## Files to Modify

1. `frontend/src/constants/index.ts` - Add `PUBLISHER_TIER_OPTIONS`
2. `frontend/src/components/book-detail/BookMetadataSection.vue` - Display logic
3. `frontend/src/components/book-detail/__tests__/BookMetadataSection.spec.ts` - Tests
