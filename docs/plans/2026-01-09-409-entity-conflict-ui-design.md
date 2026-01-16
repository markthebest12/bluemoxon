# Design: Handle 409 Entity Validation Responses in UI

**Issue:** #972
**Date:** 2026-01-09
**Status:** Approved

## Summary

When creating publishers, authors, or binders that match existing entities, the API returns 409 with suggestions. This design adds inline suggestion handling to `ComboboxWithAdd` component.

## User Flow

1. User types entity name in combobox, clicks "Add"
2. If similar entity exists, API returns 409 with suggestions
3. Suggestion panel appears below combobox showing:
   - Each match with name, confidence %, and book count (if > 0)
   - "Use" button for each suggestion
   - "Create anyway" link at bottom
4. User either selects existing entity or force-creates

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Suggestion location | Inline below combobox | Keeps user in context, less jarring than modal |
| Display pattern | Expand below (like autocomplete) | Familiar pattern, input stays visible |
| Suggestion info | Name + match% + book count (if >0) | Book count helps distinguish; hide if 0 |
| Force-create UX | Inline link, no confirmation | Duplicates are recoverable, reduces friction |
| Logic location | In ComboboxWithAdd | Self-contained, keeps consumers simple |
| Create function | Passed as prop | Flexible, no store coupling in component |
| Force parameter | Single fn with boolean | Simple API: `createFn(name, force?)` |

## Component API Changes

### ComboboxWithAdd.vue

New props:

```ts
interface Props {
  modelValue: number | null;
  label: string;
  options: Array<{ id: number; name: string }>;
  suggestedName?: string;
  // NEW: Optional async create function
  createFn?: (name: string, force?: boolean) => Promise<{ id: number; name: string }>;
}
```

New internal state:

```ts
const conflictState = ref<{
  input: string;
  suggestions: EntitySuggestion[];
} | null>(null);

const creating = ref(false);
```

### Type Definitions

```ts
interface EntitySuggestion {
  id: number;
  name: string;
  tier?: string;
  match: number;      // 0.0 - 1.0
  book_count: number;
}

interface EntityConflictResponse {
  error: "similar_entity_exists";
  entity_type: string;
  input: string;
  suggestions: EntitySuggestion[];
  resolution: string;
}
```

## Store Changes

Update create functions to accept `force` parameter:

```ts
async function createAuthor(name: string, force?: boolean): Promise<Author> {
  const url = force ? "/authors?force=true" : "/authors";
  const response = await api.post(url, { name: name.trim() });
  authors.value.push(response.data);
  return response.data;
}
// Same pattern for createPublisher, createBinder
```

## UI Structure

```vue
<div v-if="conflictState" class="suggestion-panel">
  <p class="text-sm text-amber-700 mb-2">
    Similar {{ entityLabel }} found:
  </p>

  <div v-for="s in conflictState.suggestions" :key="s.id" class="suggestion-item">
    <span>{{ s.name }}</span>
    <span class="text-gray-500">
      ({{ Math.round(s.match * 100) }}% match)
      <template v-if="s.book_count > 0">
        · {{ s.book_count }} {{ s.book_count === 1 ? 'book' : 'books' }}
      </template>
    </span>
    <button @click="selectSuggestion(s)">Use</button>
  </div>

  <a href="#" @click.prevent="forceCreate" class="text-sm text-gray-500">
    Create "{{ conflictState.input }}" anyway
  </a>
</div>
```

## Consumer Integration

ImportListingModal.vue simplified:

```vue
<!-- Before -->
<ComboboxWithAdd
  v-model="form.author_id"
  :options="refsStore.authors"
  @create="handleCreateAuthor"
/>

<!-- After -->
<ComboboxWithAdd
  v-model="form.author_id"
  :options="refsStore.authors"
  :create-fn="refsStore.createAuthor"
/>
```

Remove `handleCreateAuthor`, `handleCreatePublisher`, `handleCreateBinder` functions.

## Error Handling

1. **409 detection:** Check `getHttpStatus(error) === 409`, extract suggestions from response
2. **Empty suggestions:** Fall through to generic error (shouldn't happen)
3. **Network error on force-create:** Show inline, keep suggestions visible for retry
4. **Dismiss triggers:** Click outside, select from dropdown, successful create

## Backward Compatibility

- `@create` event still emitted when `createFn` not provided
- Existing consumers continue working without changes
- Migration is opt-in per component instance

## Files to Modify

1. `frontend/src/components/ComboboxWithAdd.vue` - Add conflict handling UI and logic
2. `frontend/src/stores/references.ts` - Add `force` param to create functions
3. `frontend/src/types/errors.ts` - Add `EntityConflictResponse` type
4. `frontend/src/components/ImportListingModal.vue` - Use new `createFn` prop
5. `frontend/src/components/AddToWatchlistModal.vue` - Use new `createFn` prop (if applicable)

## Test Plan

1. Unit tests for ComboboxWithAdd conflict state handling
2. Unit tests for store functions with force=true
3. Integration test: create entity with 409, verify suggestions appear
4. Integration test: select suggestion, verify entity selected
5. Integration test: force create, verify entity created
