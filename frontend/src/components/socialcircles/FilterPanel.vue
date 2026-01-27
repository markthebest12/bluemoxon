<!-- frontend/src/components/socialcircles/FilterPanel.vue -->
<script setup lang="ts">
/**
 * FilterPanel - Sidebar for filtering the social circles graph.
 *
 * Features:
 * - Toggle node types (authors, publishers, binders)
 * - Toggle connection types
 * - Filter by era
 * - Filter by tier
 * - Search input
 */

import { ref } from "vue";

import type { ConnectionType, Era } from "@/types/socialCircles";

// Props - uses readonly arrays since we only read, never mutate
interface Props {
  filterState: {
    readonly showAuthors: boolean;
    readonly showPublishers: boolean;
    readonly showBinders: boolean;
    readonly connectionTypes: readonly ConnectionType[];
    readonly tier1Only: boolean;
    readonly eras: readonly Era[];
    readonly searchQuery: string;
  };
}

const props = defineProps<Props>();

// Emits
type FilterKey = keyof Props["filterState"];
const emit = defineEmits<{
  "update:filter": [key: FilterKey, value: unknown];
  reset: [];
}>();

function toggleNodeType(type: "showAuthors" | "showPublishers" | "showBinders") {
  emit("update:filter", type, !props.filterState[type]);
}

// Local state
const searchQuery = ref("");

function handleReset() {
  searchQuery.value = "";
  emit("reset");
}
</script>

<template>
  <aside class="filter-panel">
    <header class="filter-panel__header">
      <h2 class="filter-panel__title">Filters</h2>
      <button type="button" class="filter-panel__reset" @click="handleReset">Reset</button>
    </header>

    <div class="filter-panel__content">
      <!-- Search -->
      <section class="filter-panel__section">
        <label class="filter-panel__label" for="search">Search</label>
        <input
          id="search"
          v-model="searchQuery"
          type="text"
          class="filter-panel__input"
          placeholder="Find person..."
        />
      </section>

      <!-- Node Types -->
      <section class="filter-panel__section">
        <h3 class="filter-panel__section-title">Node Types</h3>
        <label class="filter-panel__checkbox" @click.prevent="toggleNodeType('showAuthors')">
          <input type="checkbox" :checked="props.filterState.showAuthors" />
          <span>Authors</span>
        </label>
        <label class="filter-panel__checkbox" @click.prevent="toggleNodeType('showPublishers')">
          <input type="checkbox" :checked="props.filterState.showPublishers" />
          <span>Publishers</span>
        </label>
        <label class="filter-panel__checkbox" @click.prevent="toggleNodeType('showBinders')">
          <input type="checkbox" :checked="props.filterState.showBinders" />
          <span>Binders</span>
        </label>
      </section>

      <!-- Connection Types -->
      <section class="filter-panel__section">
        <h3 class="filter-panel__section-title">Connections</h3>
        <p class="text-sm text-victorian-ink-muted">Filter options coming soon</p>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.filter-panel {
  width: 280px;
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  border-right: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.filter-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.filter-panel__title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-victorian-hunter-700, #254a3d);
  margin: 0;
}

.filter-panel__reset {
  font-size: 0.75rem;
  color: var(--color-victorian-burgundy, #722f37);
  background: none;
  border: none;
  cursor: pointer;
}

.filter-panel__reset:hover {
  text-decoration: underline;
}

.filter-panel__content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.filter-panel__section {
  margin-bottom: 1.5rem;
}

.filter-panel__section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-bottom: 0.5rem;
}

.filter-panel__label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.filter-panel__input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  font-size: 0.875rem;
}

.filter-panel__input:focus {
  outline: none;
  border-color: var(--color-victorian-hunter-500, #3a6b5c);
}

.filter-panel__checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.25rem 0;
}
</style>
