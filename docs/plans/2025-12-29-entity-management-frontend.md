# Entity Management Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **IMPORTANT:** After completion, clean up the worktree with `git worktree remove`.

**Goal:** Add full CRUD UI for Authors, Publishers, and Binders in AdminConfigView with inline editing, search, and reassignment modals.

**Architecture:** Transform the read-only "Entity Tiers" tab into "Reference Data" with three collapsible sections, each containing a searchable table with inline tier/preferred editing, create/edit modals, and delete-with-reassignment modals.

**Tech Stack:** Vue 3, TypeScript, Composition API, Tailwind CSS, axios

---

## Task 1: Update Entity Types

**Files:**
- Modify: `frontend/src/types/admin.ts`

**Step 1: Update EntityTier interface and add new types**

Replace and add at the end of `frontend/src/types/admin.ts`:

```typescript
// Replace existing EntityTier
export interface EntityTier {
  id: number;
  name: string;
  tier: string | null;
  preferred: boolean;
  book_count: number;
}

// Add new types for forms
export interface AuthorEntity extends EntityTier {
  birth_year?: number | null;
  death_year?: number | null;
  era?: string | null;
  first_acquired_date?: string | null;
  priority_score?: number;
}

export interface PublisherEntity extends EntityTier {
  founded_year?: number | null;
  description?: string | null;
}

export interface BinderEntity extends EntityTier {
  full_name?: string | null;
  authentication_markers?: string | null;
}

export interface ReassignRequest {
  target_id: number;
}

export interface ReassignResponse {
  reassigned_count: number;
  deleted_entity: string;
  target_entity: string;
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/608-reassignment-api/frontend`
Run: `npm run type-check`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/types/admin.ts
git commit -m "feat(types): add entity management types with preferred and book_count"
```

---

## Task 2: Create EntityManagementTable Component

**Files:**
- Create: `frontend/src/components/admin/EntityManagementTable.vue`

**Step 1: Create the component**

Create directory first if needed, then create file:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { EntityTier } from "@/types/admin";

type EntityType = "author" | "publisher" | "binder";

const props = defineProps<{
  entityType: EntityType;
  entities: EntityTier[];
  loading: boolean;
  canEdit: boolean;
  searchQuery: string;
}>();

const emit = defineEmits<{
  "update:tier": [id: number, tier: string | null];
  "update:preferred": [id: number, preferred: boolean];
  edit: [entity: EntityTier];
  delete: [entity: EntityTier];
  create: [];
}>();

const tierOptions = [
  { value: null, label: "None" },
  { value: "TIER_1", label: "Tier 1" },
  { value: "TIER_2", label: "Tier 2" },
  { value: "TIER_3", label: "Tier 3" },
];

const filteredEntities = computed(() => {
  if (!props.searchQuery) return props.entities;
  const query = props.searchQuery.toLowerCase();
  return props.entities.filter((e) => e.name.toLowerCase().includes(query));
});

const entityLabel = computed(() => {
  switch (props.entityType) {
    case "author":
      return "Author";
    case "publisher":
      return "Publisher";
    case "binder":
      return "Binder";
  }
});

function handleTierChange(entity: EntityTier, event: Event) {
  const target = event.target as HTMLSelectElement;
  const newTier = target.value === "" ? null : target.value;
  emit("update:tier", entity.id, newTier);
}

function handlePreferredChange(entity: EntityTier, event: Event) {
  const target = event.target as HTMLInputElement;
  emit("update:preferred", entity.id, target.checked);
}
</script>

<template>
  <div class="entity-table">
    <!-- Header with Add button -->
    <div class="flex justify-between items-center mb-4">
      <span class="text-sm text-gray-500 dark:text-gray-400">
        {{ filteredEntities.length }} {{ entityLabel }}{{ filteredEntities.length !== 1 ? "s" : "" }}
      </span>
      <button
        v-if="canEdit"
        @click="emit('create')"
        class="px-3 py-1.5 text-sm bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700 transition-colors"
      >
        + Add {{ entityLabel }}
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center py-8 text-gray-500">Loading...</div>

    <!-- Empty state -->
    <div
      v-else-if="filteredEntities.length === 0"
      class="text-center py-8 text-gray-500 dark:text-gray-400"
    >
      {{ searchQuery ? "No matches found" : `No ${entityLabel.toLowerCase()}s yet` }}
    </div>

    <!-- Table -->
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="text-left border-b border-gray-200 dark:border-gray-700">
          <th class="pb-2 font-medium text-gray-600 dark:text-gray-300">Name</th>
          <th class="pb-2 font-medium text-gray-600 dark:text-gray-300 w-32">Tier</th>
          <th class="pb-2 font-medium text-gray-600 dark:text-gray-300 w-24 text-center">
            Preferred
          </th>
          <th class="pb-2 font-medium text-gray-600 dark:text-gray-300 w-20 text-right">Books</th>
          <th class="pb-2 font-medium text-gray-600 dark:text-gray-300 w-24 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="entity in filteredEntities"
          :key="entity.id"
          class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        >
          <td class="py-2">
            <button
              @click="emit('edit', entity)"
              class="text-left hover:text-victorian-hunter-600 dark:hover:text-victorian-gold-400 transition-colors"
              :class="{ 'cursor-default': !canEdit }"
              :disabled="!canEdit"
            >
              {{ entity.name }}
            </button>
          </td>
          <td class="py-2">
            <select
              :value="entity.tier || ''"
              @change="handleTierChange(entity, $event)"
              :disabled="!canEdit"
              class="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option v-for="opt in tierOptions" :key="opt.label" :value="opt.value || ''">
                {{ opt.label }}
              </option>
            </select>
          </td>
          <td class="py-2 text-center">
            <input
              type="checkbox"
              :checked="entity.preferred"
              @change="handlePreferredChange(entity, $event)"
              :disabled="!canEdit"
              class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-victorian-hunter-600 focus:ring-victorian-hunter-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </td>
          <td class="py-2 text-right tabular-nums text-gray-600 dark:text-gray-400">
            {{ entity.book_count }}
          </td>
          <td class="py-2 text-right">
            <div class="flex justify-end gap-2">
              <button
                v-if="canEdit"
                @click="emit('edit', entity)"
                class="text-gray-500 hover:text-victorian-hunter-600 dark:hover:text-victorian-gold-400"
                title="Edit"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
              </button>
              <button
                v-if="canEdit"
                @click="emit('delete', entity)"
                class="text-gray-500 hover:text-red-600 dark:hover:text-red-400"
                title="Delete"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

**Step 2: Verify TypeScript compiles**

Run: `npm run type-check`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/admin/EntityManagementTable.vue
git commit -m "feat(ui): add EntityManagementTable component with inline editing"
```

---

## Task 3: Create EntityFormModal Component

**Files:**
- Create: `frontend/src/components/admin/EntityFormModal.vue`

**Step 1: Create the modal component**

```vue
<script setup lang="ts">
import { ref, computed, watch } from "vue";
import TransitionModal from "@/components/TransitionModal.vue";
import type { AuthorEntity, PublisherEntity, BinderEntity } from "@/types/admin";

type EntityType = "author" | "publisher" | "binder";
type Entity = AuthorEntity | PublisherEntity | BinderEntity;

const props = defineProps<{
  visible: boolean;
  entityType: EntityType;
  entity?: Entity | null;
  saving: boolean;
  error?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  save: [data: Partial<Entity>];
}>();

const tierOptions = [
  { value: "", label: "None" },
  { value: "TIER_1", label: "Tier 1" },
  { value: "TIER_2", label: "Tier 2" },
  { value: "TIER_3", label: "Tier 3" },
];

// Form state
const form = ref<Partial<Entity>>({});

const isEdit = computed(() => !!props.entity?.id);
const title = computed(() => {
  const label =
    props.entityType === "author"
      ? "Author"
      : props.entityType === "publisher"
        ? "Publisher"
        : "Binder";
  return isEdit.value ? `Edit ${label}` : `Add ${label}`;
});

// Reset form when entity changes
watch(
  () => props.entity,
  (newEntity) => {
    if (newEntity) {
      form.value = { ...newEntity };
    } else {
      form.value = {
        name: "",
        tier: null,
        preferred: false,
      };
    }
  },
  { immediate: true }
);

function handleSubmit() {
  if (!form.value.name?.trim()) return;
  emit("save", form.value);
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="emit('close')">
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-md mx-4 overflow-hidden"
    >
      <!-- Header -->
      <div
        class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center"
      >
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ title }}</h2>
        <button
          @click="emit('close')"
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="px-6 py-4 flex flex-col gap-4">
        <!-- Error -->
        <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded text-sm">
          {{ error }}
        </div>

        <!-- Name (all types) -->
        <label class="block">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Name *</span>
          <input
            v-model="form.name"
            type="text"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-victorian-hunter-500 focus:border-victorian-hunter-500"
          />
        </label>

        <!-- Tier (all types) -->
        <label class="block">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Tier</span>
          <select
            v-model="form.tier"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-victorian-hunter-500 focus:border-victorian-hunter-500"
          >
            <option v-for="opt in tierOptions" :key="opt.label" :value="opt.value || null">
              {{ opt.label }}
            </option>
          </select>
        </label>

        <!-- Preferred (all types) -->
        <label class="flex items-center gap-2">
          <input
            v-model="form.preferred"
            type="checkbox"
            class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-victorian-hunter-600 focus:ring-victorian-hunter-500"
          />
          <span class="text-sm text-gray-700 dark:text-gray-300">Preferred (+10 scoring bonus)</span>
        </label>

        <!-- Author-specific fields -->
        <template v-if="entityType === 'author'">
          <div class="grid grid-cols-2 gap-4">
            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Birth Year</span>
              <input
                v-model.number="(form as AuthorEntity).birth_year"
                type="number"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </label>
            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Death Year</span>
              <input
                v-model.number="(form as AuthorEntity).death_year"
                type="number"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </label>
          </div>
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Era</span>
            <input
              v-model="(form as AuthorEntity).era"
              type="text"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
        </template>

        <!-- Publisher-specific fields -->
        <template v-if="entityType === 'publisher'">
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Founded Year</span>
            <input
              v-model.number="(form as PublisherEntity).founded_year"
              type="number"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Description</span>
            <textarea
              v-model="(form as PublisherEntity).description"
              rows="3"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
        </template>

        <!-- Binder-specific fields -->
        <template v-if="entityType === 'binder'">
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Full Name</span>
            <input
              v-model="(form as BinderEntity).full_name"
              type="text"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              Authentication Markers
            </span>
            <textarea
              v-model="(form as BinderEntity).authentication_markers"
              rows="3"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
        </template>
      </form>

      <!-- Footer -->
      <div
        class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3 bg-gray-50 dark:bg-gray-800/50"
      >
        <button
          type="button"
          @click="emit('close')"
          class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        >
          Cancel
        </button>
        <button
          @click="handleSubmit"
          :disabled="saving || !form.name?.trim()"
          class="px-4 py-2 text-sm bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ saving ? "Saving..." : isEdit ? "Save Changes" : "Create" }}
        </button>
      </div>
    </div>
  </TransitionModal>
</template>
```

**Step 2: Verify TypeScript compiles**

Run: `npm run type-check`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/admin/EntityFormModal.vue
git commit -m "feat(ui): add EntityFormModal component for create/edit"
```

---

## Task 4: Create ReassignDeleteModal Component

**Files:**
- Create: `frontend/src/components/admin/ReassignDeleteModal.vue`

**Step 1: Create the modal component**

```vue
<script setup lang="ts">
import { ref, computed, watch } from "vue";
import TransitionModal from "@/components/TransitionModal.vue";
import type { EntityTier } from "@/types/admin";

const props = defineProps<{
  visible: boolean;
  entity: EntityTier | null;
  allEntities: EntityTier[];
  entityLabel: string;
  processing: boolean;
  error?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  "delete-direct": [];
  "reassign-delete": [targetId: number];
}>();

const selectedTargetId = ref<number | null>(null);

// Available targets (exclude self)
const targetOptions = computed(() => {
  if (!props.entity) return [];
  return props.allEntities.filter((e) => e.id !== props.entity!.id);
});

const hasBooks = computed(() => props.entity && props.entity.book_count > 0);

// Reset selection when modal opens
watch(
  () => props.visible,
  (isVisible) => {
    if (isVisible) {
      selectedTargetId.value = null;
    }
  }
);

function handleDelete() {
  if (hasBooks.value && selectedTargetId.value) {
    emit("reassign-delete", selectedTargetId.value);
  } else if (!hasBooks.value) {
    emit("delete-direct");
  }
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="emit('close')">
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-md mx-4 overflow-hidden"
    >
      <!-- Header -->
      <div
        class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center"
      >
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Delete {{ entityLabel }}
        </h2>
        <button
          @click="emit('close')"
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="px-6 py-4">
        <!-- Error -->
        <div
          v-if="error"
          class="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded text-sm"
        >
          {{ error }}
        </div>

        <div v-if="entity">
          <!-- Entity info -->
          <div class="mb-4">
            <p class="text-gray-900 dark:text-gray-100 font-medium">{{ entity.name }}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ entity.book_count }} associated book{{ entity.book_count !== 1 ? "s" : "" }}
            </p>
          </div>

          <!-- No books - simple delete -->
          <div v-if="!hasBooks" class="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded">
            <p class="text-sm text-yellow-800 dark:text-yellow-200">
              This {{ entityLabel.toLowerCase() }} has no books. It will be permanently deleted.
            </p>
          </div>

          <!-- Has books - must reassign -->
          <div v-else class="flex flex-col gap-4">
            <div class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded">
              <p class="text-sm text-amber-800 dark:text-amber-200">
                This {{ entityLabel.toLowerCase() }} has {{ entity.book_count }} book{{
                  entity.book_count !== 1 ? "s" : ""
                }}. Select a target to reassign them before deletion.
              </p>
            </div>

            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                Reassign books to *
              </span>
              <select
                v-model="selectedTargetId"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-victorian-hunter-500 focus:border-victorian-hunter-500"
              >
                <option :value="null" disabled>Select target {{ entityLabel.toLowerCase() }}</option>
                <option v-for="target in targetOptions" :key="target.id" :value="target.id">
                  {{ target.name }} ({{ target.book_count }} books)
                </option>
              </select>
            </label>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div
        class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3 bg-gray-50 dark:bg-gray-800/50"
      >
        <button
          type="button"
          @click="emit('close')"
          class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        >
          Cancel
        </button>
        <button
          @click="handleDelete"
          :disabled="processing || (hasBooks && !selectedTargetId)"
          class="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ processing ? "Processing..." : hasBooks ? "Reassign & Delete" : "Delete" }}
        </button>
      </div>
    </div>
  </TransitionModal>
</template>
```

**Step 2: Verify TypeScript compiles**

Run: `npm run type-check`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/admin/ReassignDeleteModal.vue
git commit -m "feat(ui): add ReassignDeleteModal component for delete with reassignment"
```

---

## Task 5: Update AdminConfigView - Part 1 (Script Setup)

**Files:**
- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1: Update imports and add new state**

At the top of `<script setup>`, add new imports and modify tab type:

```typescript
import { ref, onMounted, computed } from "vue";
import { api } from "@/services/api";
import type {
  SystemInfoResponse,
  CostResponse,
  EntityTier,
  AuthorEntity,
  PublisherEntity,
  BinderEntity,
} from "@/types/admin";
import EntityManagementTable from "@/components/admin/EntityManagementTable.vue";
import EntityFormModal from "@/components/admin/EntityFormModal.vue";
import ReassignDeleteModal from "@/components/admin/ReassignDeleteModal.vue";

// Tab state - rename 'tiers' to 'reference'
const activeTab = ref<"settings" | "status" | "scoring" | "reference" | "costs">("settings");
```

**Step 2: Add entity management state after existing state**

After the `costError` line (~line 22), add:

```typescript
// Entity management state
const authors = ref<AuthorEntity[]>([]);
const publishers = ref<PublisherEntity[]>([]);
const binders = ref<BinderEntity[]>([]);
const loadingEntities = ref({ authors: false, publishers: false, binders: false });

// Search filters
const searchFilters = ref({ authors: "", publishers: "", binders: "" });

// Collapsed sections
const collapsedSections = ref({ authors: false, publishers: false, binders: false });

// Modal state
type EntityType = "author" | "publisher" | "binder";
const formModal = ref({
  visible: false,
  entityType: "author" as EntityType,
  entity: null as EntityTier | null,
  saving: false,
  error: null as string | null,
});

const deleteModal = ref({
  visible: false,
  entityType: "author" as EntityType,
  entity: null as EntityTier | null,
  processing: false,
  error: null as string | null,
});

// Permission check (placeholder - implement based on your auth system)
const canEdit = computed(() => true); // TODO: Check userStore.isEditor
```

**Step 3: Add entity loading functions after existing loadSystemInfo function**

After the `refreshSystemInfo` function (~line 88), add:

```typescript
// Entity management functions
async function loadEntities() {
  loadingEntities.value = { authors: true, publishers: true, binders: true };
  try {
    const [authorsRes, publishersRes, bindersRes] = await Promise.all([
      api.get("/authors"),
      api.get("/publishers"),
      api.get("/binders"),
    ]);
    authors.value = authorsRes.data;
    publishers.value = publishersRes.data;
    binders.value = bindersRes.data;
  } catch (e) {
    console.error("Failed to load entities:", e);
  } finally {
    loadingEntities.value = { authors: false, publishers: false, binders: false };
  }
}

function getEntitiesByType(type: EntityType): EntityTier[] {
  switch (type) {
    case "author":
      return authors.value;
    case "publisher":
      return publishers.value;
    case "binder":
      return binders.value;
  }
}

function getEntityLabel(type: EntityType): string {
  switch (type) {
    case "author":
      return "Author";
    case "publisher":
      return "Publisher";
    case "binder":
      return "Binder";
  }
}

function toggleSection(type: EntityType) {
  collapsedSections.value[type + "s" as keyof typeof collapsedSections.value] =
    !collapsedSections.value[type + "s" as keyof typeof collapsedSections.value];
}
```

**Step 4: Commit partial progress**

```bash
git add frontend/src/views/AdminConfigView.vue
git commit -m "feat(admin): add entity management state and loading functions"
```

---

## Task 6: Update AdminConfigView - Part 2 (CRUD Handlers)

**Files:**
- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1: Add CRUD handler functions**

After the `toggleSection` function, add:

```typescript
// Inline update handlers
async function handleTierUpdate(type: EntityType, id: number, tier: string | null) {
  const endpoint = `/${type}s/${id}`;
  try {
    await api.put(endpoint, { tier });
    // Update local state
    const entities = getEntitiesByType(type);
    const entity = entities.find((e) => e.id === id);
    if (entity) entity.tier = tier;
  } catch (e) {
    console.error(`Failed to update ${type} tier:`, e);
    // Reload to revert
    await loadEntities();
  }
}

async function handlePreferredUpdate(type: EntityType, id: number, preferred: boolean) {
  const endpoint = `/${type}s/${id}`;
  try {
    await api.put(endpoint, { preferred });
    // Update local state
    const entities = getEntitiesByType(type);
    const entity = entities.find((e) => e.id === id);
    if (entity) entity.preferred = preferred;
  } catch (e) {
    console.error(`Failed to update ${type} preferred:`, e);
    await loadEntities();
  }
}

// Modal handlers
function openCreateModal(type: EntityType) {
  formModal.value = {
    visible: true,
    entityType: type,
    entity: null,
    saving: false,
    error: null,
  };
}

function openEditModal(type: EntityType, entity: EntityTier) {
  formModal.value = {
    visible: true,
    entityType: type,
    entity,
    saving: false,
    error: null,
  };
}

function closeFormModal() {
  formModal.value.visible = false;
}

async function handleFormSave(type: EntityType, data: Partial<EntityTier>) {
  formModal.value.saving = true;
  formModal.value.error = null;

  try {
    if (formModal.value.entity?.id) {
      // Update
      await api.put(`/${type}s/${formModal.value.entity.id}`, data);
    } else {
      // Create
      await api.post(`/${type}s`, data);
    }
    closeFormModal();
    await loadEntities();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    formModal.value.error = err.response?.data?.detail || "Failed to save";
  } finally {
    formModal.value.saving = false;
  }
}

function openDeleteModal(type: EntityType, entity: EntityTier) {
  deleteModal.value = {
    visible: true,
    entityType: type,
    entity,
    processing: false,
    error: null,
  };
}

function closeDeleteModal() {
  deleteModal.value.visible = false;
}

async function handleDeleteDirect(type: EntityType) {
  if (!deleteModal.value.entity) return;
  deleteModal.value.processing = true;
  deleteModal.value.error = null;

  try {
    await api.delete(`/${type}s/${deleteModal.value.entity.id}`);
    closeDeleteModal();
    await loadEntities();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    deleteModal.value.error = err.response?.data?.detail || "Failed to delete";
  } finally {
    deleteModal.value.processing = false;
  }
}

async function handleReassignDelete(type: EntityType, targetId: number) {
  if (!deleteModal.value.entity) return;
  deleteModal.value.processing = true;
  deleteModal.value.error = null;

  try {
    await api.post(`/${type}s/${deleteModal.value.entity.id}/reassign`, {
      target_id: targetId,
    });
    closeDeleteModal();
    await loadEntities();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    deleteModal.value.error = err.response?.data?.detail || "Failed to reassign and delete";
  } finally {
    deleteModal.value.processing = false;
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/views/AdminConfigView.vue
git commit -m "feat(admin): add CRUD and modal handlers for entity management"
```

---

## Task 7: Update AdminConfigView - Part 3 (Template)

**Files:**
- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1: Update tab navigation in template**

Find the "Entity Tiers" tab button (~line 252-262) and change to "Reference Data":

```vue
        <button
          @click="
            activeTab = 'reference';
            if (!authors.length) loadEntities();
          "
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'reference'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Reference Data
        </button>
```

**Step 2: Replace Entity Tiers tab content**

Find the `<!-- Entity Tiers Tab -->` section (~line 631-701) and replace entirely with:

```vue
    <!-- Reference Data Tab -->
    <div v-else-if="activeTab === 'reference'" class="flex flex-col gap-6">
      <!-- Authors Section -->
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-sm">
        <button
          @click="toggleSection('author')"
          class="w-full px-6 py-4 flex items-center justify-between text-left border-b border-gray-200 dark:border-gray-700"
        >
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Authors</h3>
          <svg
            class="w-5 h-5 text-gray-500 transition-transform"
            :class="{ 'rotate-180': !collapsedSections.authors }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <div v-if="!collapsedSections.authors" class="p-6">
          <input
            v-model="searchFilters.authors"
            type="text"
            placeholder="Search authors..."
            class="mb-4 w-full max-w-xs px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
          <EntityManagementTable
            entity-type="author"
            :entities="authors"
            :loading="loadingEntities.authors"
            :can-edit="canEdit"
            :search-query="searchFilters.authors"
            @update:tier="(id, tier) => handleTierUpdate('author', id, tier)"
            @update:preferred="(id, pref) => handlePreferredUpdate('author', id, pref)"
            @edit="(e) => openEditModal('author', e)"
            @delete="(e) => openDeleteModal('author', e)"
            @create="openCreateModal('author')"
          />
        </div>
      </div>

      <!-- Publishers Section -->
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-sm">
        <button
          @click="toggleSection('publisher')"
          class="w-full px-6 py-4 flex items-center justify-between text-left border-b border-gray-200 dark:border-gray-700"
        >
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Publishers</h3>
          <svg
            class="w-5 h-5 text-gray-500 transition-transform"
            :class="{ 'rotate-180': !collapsedSections.publishers }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <div v-if="!collapsedSections.publishers" class="p-6">
          <input
            v-model="searchFilters.publishers"
            type="text"
            placeholder="Search publishers..."
            class="mb-4 w-full max-w-xs px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
          <EntityManagementTable
            entity-type="publisher"
            :entities="publishers"
            :loading="loadingEntities.publishers"
            :can-edit="canEdit"
            :search-query="searchFilters.publishers"
            @update:tier="(id, tier) => handleTierUpdate('publisher', id, tier)"
            @update:preferred="(id, pref) => handlePreferredUpdate('publisher', id, pref)"
            @edit="(e) => openEditModal('publisher', e)"
            @delete="(e) => openDeleteModal('publisher', e)"
            @create="openCreateModal('publisher')"
          />
        </div>
      </div>

      <!-- Binders Section -->
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-sm">
        <button
          @click="toggleSection('binder')"
          class="w-full px-6 py-4 flex items-center justify-between text-left border-b border-gray-200 dark:border-gray-700"
        >
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Binders</h3>
          <svg
            class="w-5 h-5 text-gray-500 transition-transform"
            :class="{ 'rotate-180': !collapsedSections.binders }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <div v-if="!collapsedSections.binders" class="p-6">
          <input
            v-model="searchFilters.binders"
            type="text"
            placeholder="Search binders..."
            class="mb-4 w-full max-w-xs px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
          <EntityManagementTable
            entity-type="binder"
            :entities="binders"
            :loading="loadingEntities.binders"
            :can-edit="canEdit"
            :search-query="searchFilters.binders"
            @update:tier="(id, tier) => handleTierUpdate('binder', id, tier)"
            @update:preferred="(id, pref) => handlePreferredUpdate('binder', id, pref)"
            @edit="(e) => openEditModal('binder', e)"
            @delete="(e) => openDeleteModal('binder', e)"
            @create="openCreateModal('binder')"
          />
        </div>
      </div>
    </div>
```

**Step 3: Add modals at end of template (before closing `</div>`)**

```vue
    <!-- Entity Form Modal -->
    <EntityFormModal
      :visible="formModal.visible"
      :entity-type="formModal.entityType"
      :entity="formModal.entity"
      :saving="formModal.saving"
      :error="formModal.error"
      @close="closeFormModal"
      @save="(data) => handleFormSave(formModal.entityType, data)"
    />

    <!-- Reassign Delete Modal -->
    <ReassignDeleteModal
      :visible="deleteModal.visible"
      :entity="deleteModal.entity"
      :all-entities="getEntitiesByType(deleteModal.entityType)"
      :entity-label="getEntityLabel(deleteModal.entityType)"
      :processing="deleteModal.processing"
      :error="deleteModal.error"
      @close="closeDeleteModal"
      @delete-direct="handleDeleteDirect(deleteModal.entityType)"
      @reassign-delete="(targetId) => handleReassignDelete(deleteModal.entityType, targetId)"
    />
  </div>
</template>
```

**Step 4: Commit**

```bash
git add frontend/src/views/AdminConfigView.vue
git commit -m "feat(admin): update template with entity management UI"
```

---

## Task 8: Remove Dead Code

**Files:**
- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1: Remove unused grouped entity functions**

Find and remove these functions (they're no longer needed):
- `groupedAuthors`
- `groupedPublishers`
- `groupedBinders`
- `groupByTier`
- `formatTierLabel`

**Step 2: Verify TypeScript compiles**

Run: `npm run type-check`
Expected: No errors

**Step 3: Run linter**

Run: `npm run lint`
Expected: No errors (or auto-fixed)

**Step 4: Commit**

```bash
git add frontend/src/views/AdminConfigView.vue
git commit -m "refactor(admin): remove unused tier grouping functions"
```

---

## Task 9: Final Validation

**Step 1: Run type check**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/608-reassignment-api/frontend`
Run: `npm run type-check`
Expected: No errors

**Step 2: Run linter**

Run: `npm run lint`
Expected: No errors

**Step 3: Run frontend tests**

Run: `npm run test`
Expected: All tests pass

**Step 4: Build check**

Run: `npm run build`
Expected: Build succeeds

---

## Task 10: Push and Create PR

**Step 1: Check git status**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/608-reassignment-api`
Run: `git status`

**Step 2: Review commits**

Run: `git log --oneline -10`

**Step 3: Push to origin**

Run: `git push -u origin feat/608-entity-reassignment`

**Step 4: Create PR**

```bash
gh pr create --base staging --title "feat: Add entity management UI for Authors, Publishers, Binders (#608)" --body "## Summary
- Add EntityManagementTable component with inline tier/preferred editing
- Add EntityFormModal for create/edit operations
- Add ReassignDeleteModal for delete with book reassignment
- Transform 'Entity Tiers' tab to 'Reference Data' with full CRUD
- Support dark mode throughout

## Changes
- **Types**: Added entity types with id, preferred, book_count
- **Components**: 3 new admin components
- **AdminConfigView**: Complete rewrite of entity tab

## Test Plan
- [ ] CI passes
- [ ] Manual test: Create/Edit/Delete authors, publishers, binders
- [ ] Manual test: Inline tier and preferred editing
- [ ] Manual test: Search filtering
- [ ] Manual test: Reassign books before delete
- [ ] Manual test: Dark mode appearance

## Related
- Part 3 of 3 for #608
- Backend: PR #649 (merged)
- Reassignment API: PR #661 (merged)"
```

---

## Summary

This plan adds the Entity Management UI with:
- **EntityManagementTable**: Inline editing for tier/preferred, search, CRUD buttons
- **EntityFormModal**: Create/edit with type-specific fields
- **ReassignDeleteModal**: Delete with optional book reassignment
- **AdminConfigView**: Transformed "Entity Tiers" → "Reference Data" tab

Total commits: ~8 (types, table, form modal, delete modal, state, handlers, template, cleanup)
