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
  savingIds: Set<string>;
}>();

// Check if an entity is currently being saved
function isEntitySaving(entity: EntityTier): boolean {
  const key = `${props.entityType}-${entity.id}`;
  return props.savingIds.has(key);
}

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
  let result = [...props.entities];

  // Filter by search query
  if (props.searchQuery) {
    const query = props.searchQuery.toLowerCase();
    result = result.filter((e) => e.name.toLowerCase().includes(query));
  }

  // Sort: preferred first, then by tier (1 > 2 > 3 > none), then alphabetically
  return result.sort((a, b) => {
    // Preferred entities first
    if (a.preferred !== b.preferred) return a.preferred ? -1 : 1;
    // Then by tier (TIER_1 > TIER_2 > TIER_3 > null)
    const tierOrder = { TIER_1: 1, TIER_2: 2, TIER_3: 3 };
    const aTier = a.tier ? tierOrder[a.tier as keyof typeof tierOrder] || 4 : 4;
    const bTier = b.tier ? tierOrder[b.tier as keyof typeof tierOrder] || 4 : 4;
    if (aTier !== bTier) return aTier - bTier;
    // Then alphabetically
    return a.name.localeCompare(b.name);
  });
});

const entityLabel = computed(() => {
  switch (props.entityType) {
    case "author":
      return "Author";
    case "publisher":
      return "Publisher";
    case "binder":
      return "Binder";
    default:
      return "Entity";
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
      <span class="text-sm text-gray-500">
        {{ filteredEntities.length }} {{ entityLabel
        }}{{ filteredEntities.length !== 1 ? "s" : "" }}
      </span>
      <button
        v-if="canEdit"
        class="px-3 py-1.5 text-sm bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700 transition-colors"
        @click="emit('create')"
      >
        + Add {{ entityLabel }}
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center py-8 text-gray-500">Loading...</div>

    <!-- Empty state -->
    <div v-else-if="filteredEntities.length === 0" class="text-center py-8 text-gray-500">
      {{ searchQuery ? "No matches found" : `No ${entityLabel.toLowerCase()}s yet` }}
    </div>

    <!-- Table -->
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="text-left border-b border-gray-200">
          <th class="pb-2 font-medium text-gray-600">Name</th>
          <th class="pb-2 font-medium text-gray-600 w-32">Tier</th>
          <th class="pb-2 font-medium text-gray-600 w-24 text-center">Preferred</th>
          <th class="pb-2 font-medium text-gray-600 w-20 text-right">Books</th>
          <th class="pb-2 font-medium text-gray-600 w-24 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="entity in filteredEntities"
          :key="entity.id"
          class="border-b border-gray-100 hover:bg-gray-50"
        >
          <td class="py-2">
            <button
              class="text-left hover:text-victorian-hunter-600 transition-colors"
              :class="{ 'cursor-default': !canEdit }"
              :disabled="!canEdit"
              @click="emit('edit', entity)"
            >
              {{ entity.name }}
            </button>
          </td>
          <td class="py-2">
            <div class="flex items-center gap-2">
              <select
                :value="entity.tier || ''"
                :disabled="!canEdit || isEntitySaving(entity)"
                class="w-full px-2 py-1 text-sm border border-gray-300 rounded bg-white disabled:opacity-50 disabled:cursor-not-allowed"
                @change="handleTierChange(entity, $event)"
              >
                <option v-for="opt in tierOptions" :key="opt.label" :value="opt.value || ''">
                  {{ opt.label }}
                </option>
              </select>
              <!-- Saving spinner -->
              <svg
                v-if="isEntitySaving(entity)"
                data-testid="saving-spinner"
                class="w-4 h-4 animate-spin text-victorian-hunter-600"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            </div>
          </td>
          <td class="py-2 text-center">
            <input
              type="checkbox"
              :checked="entity.preferred"
              :disabled="!canEdit || isEntitySaving(entity)"
              class="w-4 h-4 rounded border-gray-300 text-victorian-hunter-600 focus:ring-victorian-hunter-500 disabled:opacity-50 disabled:cursor-not-allowed"
              @change="handlePreferredChange(entity, $event)"
            />
          </td>
          <td class="py-2 text-right tabular-nums text-gray-600">{{ entity.book_count }}</td>
          <td class="py-2 text-right">
            <div class="flex justify-end gap-2">
              <button
                v-if="canEdit"
                class="text-gray-500 hover:text-victorian-hunter-600"
                title="Edit"
                @click="emit('edit', entity)"
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
                class="text-gray-500 hover:text-[var(--color-status-error-accent)]"
                title="Delete"
                @click="emit('delete', entity)"
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
