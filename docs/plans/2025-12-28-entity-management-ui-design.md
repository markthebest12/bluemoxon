# Entity Management UI Design

**Issue:** [#608](https://github.com/bluemoxon/bluemoxon/issues/608)
**Date:** 2025-12-28
**Status:** Approved

## Overview

Add CRUD management UI for Authors, Publishers, and Binders within the existing AdminConfigView. Enables editors to manage tier levels (1, 2, 3), preferred status, and merge duplicate entities.

## Design Decisions

1. **UI Location**: Extend existing AdminConfigView "Entity Tiers" tab (rename to "Reference Data")
2. **Preferred Scope**: All three entities get a `preferred` boolean field
3. **Scoring Impact**: Preferred adds +10 bonus points (additive, on top of tier bonuses)
4. **Edit Pattern**: Inline editing (dropdowns/checkboxes) for tier and preferred, auto-save on change
5. **CRUD Scope**: Full CRUD + reassignment (merge duplicates by reassigning books before delete)
6. **Reassignment UX**: Pre-delete modal shows book count, dropdown to select target entity
7. **Tab Layout**: Unified view with three collapsible sections
8. **Filtering**: Simple text search box per section to filter by name

---

## Database Changes

### New Fields

Add `preferred` boolean to all three entity models:

```python
# backend/app/models/author.py
preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

# backend/app/models/publisher.py
preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

# backend/app/models/binder.py
preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

### Migration

Single Alembic migration adding `preferred` column (default `False`) to `authors`, `publishers`, and `binders` tables.

```python
def upgrade():
    op.add_column('authors', sa.Column('preferred', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('publishers', sa.Column('preferred', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('binders', sa.Column('preferred', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    op.drop_column('binders', 'preferred')
    op.drop_column('publishers', 'preferred')
    op.drop_column('authors', 'preferred')
```

---

## Scoring Engine Updates

### New Constant

```python
# backend/app/services/tiered_scoring.py
PREFERRED_BONUS = 10  # Points added for each preferred entity
```

### Quality Score Calculation

Add preferred bonuses in `calculate_quality_score()`:

```python
# After tier bonuses
if book.author and book.author.preferred:
    score += PREFERRED_BONUS
if book.publisher and book.publisher.preferred:
    score += PREFERRED_BONUS
if book.binder and book.binder.preferred:
    score += PREFERRED_BONUS
```

### Config Exposure

Update `/admin/system-info` to include `preferred_bonus` in scoring config.

---

## API Changes

### Schema Updates

Add `preferred: bool` to all Create/Update/Response schemas:

```python
# backend/app/schemas/reference.py

class AuthorCreate(BaseModel):
    name: str
    tier: str | None = None
    preferred: bool = False
    # ... existing fields

class AuthorUpdate(BaseModel):
    name: str | None = None
    tier: str | None = None
    preferred: bool | None = None
    # ... existing fields

class AuthorResponse(BaseModel):
    id: int
    name: str
    tier: str | None
    preferred: bool
    book_count: int
    # ... existing fields
```

Same pattern for Publisher and Binder schemas.

### New Reassignment Endpoints

```python
# backend/app/api/v1/authors.py

@router.post("/{author_id}/reassign", response_model=ReassignResponse)
@require_editor
async def reassign_author_books(
    author_id: int,
    body: ReassignRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reassign all books from source author to target author, then delete source.
    """
    # 1. Validate source and target exist
    # 2. Update all books with author_id to target_id
    # 3. Delete source author
    # 4. Return count of reassigned books
```

Request/Response:
```python
class ReassignRequest(BaseModel):
    target_id: int

class ReassignResponse(BaseModel):
    reassigned_count: int
    deleted_entity: str
    target_entity: str
```

Same pattern for `/publishers/{id}/reassign` and `/binders/{id}/reassign`.

---

## Frontend Components

### EntityManagementTable.vue

Reusable component for each entity section.

**Props:**
```typescript
interface Props {
  entityType: 'author' | 'publisher' | 'binder'
  entities: Entity[]
  loading: boolean
  canEdit: boolean
}
```

**Table Columns:**
| Column | Type | Notes |
|--------|------|-------|
| Name | Text | Click opens edit modal |
| Tier | Dropdown (inline) | TIER_1, TIER_2, TIER_3, null |
| Preferred | Checkbox (inline) | Auto-saves on toggle |
| Books | Number (read-only) | Count with link |
| Actions | Buttons | Edit, Delete |

**Events:**
- `@update:tier` - Inline tier change
- `@update:preferred` - Inline preferred toggle
- `@edit` - Open edit modal
- `@delete` - Open delete/reassign modal
- `@create` - Open create modal

### EntityFormModal.vue

Shared modal for create/edit operations.

**Author fields:** name, tier, preferred, birth_year, death_year, era, priority_score
**Publisher fields:** name, tier, preferred, founded_year, description
**Binder fields:** name, full_name, tier, preferred, authentication_markers

### ReassignDeleteModal.vue

Modal for delete with reassignment.

**Content:**
- Shows entity name and book count
- Dropdown to select target entity (excludes self)
- "Reassign and Delete" button (disabled until target selected)
- Cancel button

---

## AdminConfigView Integration

### Tab Rename

"Entity Tiers" → "Reference Data"

### Tab Structure

```vue
<template>
  <div class="reference-data-tab">
    <EntitySection
      v-for="type in ['authors', 'publishers', 'binders']"
      :key="type"
      :entity-type="type"
      :collapsed="collapsedSections[type]"
      @toggle="toggleSection(type)"
    >
      <template #header>
        <SearchInput v-model="searchFilters[type]" />
        <AddButton @click="openCreateModal(type)" :disabled="!canEdit" />
      </template>

      <EntityManagementTable
        :entities="filteredEntities[type]"
        :can-edit="canEdit"
        @update:tier="handleTierUpdate"
        @update:preferred="handlePreferredUpdate"
        @edit="openEditModal"
        @delete="openDeleteModal"
      />
    </EntitySection>
  </div>
</template>
```

### Data Flow

1. On tab mount, fetch all three entity lists in parallel
2. Store in reactive state with loading flags
3. Filter client-side based on search input
4. Mutations trigger optimistic UI update + API call
5. On error, revert UI and show toast

### Permissions

- Read: All authenticated users
- Write: Editor role (check `userStore.isEditor`)
- Non-editors: Disabled controls with "Editor role required" tooltip

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Inline edit fails | Revert UI, show toast with retry |
| Modal submit fails | Keep open, show inline error |
| Reassign fails | Keep modal, show error, don't delete |
| Delete fails | Toast with error details |
| Network timeout | Auto-retry with "Retrying..." indicator |

---

## Testing Strategy

### Backend (pytest)

**Unit tests:**
- `test_preferred_bonus_scoring` - Verify +10 points per preferred entity
- `test_reassign_moves_books` - Books correctly moved to target
- `test_reassign_deletes_source` - Source entity deleted after move
- `test_delete_blocked_with_books` - 409 when books exist (existing behavior)

**Integration tests:**
- Full CRUD cycle for each entity type
- Reassign workflow end-to-end

### Frontend (Vitest)

**Component tests:**
- `EntityManagementTable` renders entities correctly
- Inline tier dropdown triggers API call
- Preferred checkbox toggles correctly
- Search filters entities
- Edit/Delete buttons emit events

### E2E (Playwright)

- Create new author with all fields
- Edit author tier and preferred inline
- Delete author with no books
- Reassign author books and delete
- Verify scoring updates after preferred change

---

## Rollback Plan

1. **Feature flag**: `ENABLE_ENTITY_MANAGEMENT_UI` (environment variable)
   - Default `false` in production initially
   - UI hidden when disabled, API endpoints still work

2. **Migration safety**:
   - Adding columns is non-breaking
   - Default `false` means no scoring change until explicitly set

3. **Revert path**:
   - Disable feature flag to hide UI
   - No data migration needed
   - Preferred values preserved for re-enable

---

## Implementation Phases

### Phase 1: Backend Foundation
- Add `preferred` field to models
- Create migration
- Update schemas
- Update existing CRUD endpoints

### Phase 2: Scoring Integration
- Add `PREFERRED_BONUS` constant
- Update scoring calculation
- Update admin system-info endpoint
- Add unit tests

### Phase 3: Reassignment API
- Create reassign endpoints (3)
- Add validation and error handling
- Add integration tests

### Phase 4: Frontend Components
- Create EntityManagementTable component
- Create EntityFormModal component
- Create ReassignDeleteModal component
- Add component tests

### Phase 5: AdminConfigView Integration
- Rename tab to "Reference Data"
- Replace read-only display with new components
- Wire up data fetching and mutations
- Add permission checks

### Phase 6: E2E Testing & Polish
- Add Playwright tests
- Add feature flag
- Final UI polish
- Documentation
