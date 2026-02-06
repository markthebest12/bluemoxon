<!-- frontend/src/components/socialcircles/FilterPanel.vue -->
<script setup lang="ts">
/**
 * FilterPanel - Sidebar for filtering the social circles graph.
 *
 * Features:
 * - Toggle node types (authors, publishers, binders)
 * - Toggle connection types with color indicators
 * - Filter by era
 * - Tier 1 only toggle
 * - Search input
 */

import { ref, watch } from "vue";

import FilterBadges from "@/components/socialcircles/FilterBadges.vue";
import type { ApiNode, ConnectionType, Era } from "@/types/socialCircles";

// Connection type display info
const CONNECTION_INFO: Record<ConnectionType, { label: string; color: string }> = {
  // Book-based connections
  publisher: { label: "Published By", color: "#4ade80" },
  shared_publisher: { label: "Shared Publisher", color: "#4ade80" },
  binder: { label: "Same Bindery", color: "#a78bfa" },
  // AI-discovered connections
  family: { label: "Family", color: "#60a5fa" },
  friendship: { label: "Friendship", color: "#60a5fa" },
  influence: { label: "Influence", color: "#60a5fa" },
  collaboration: { label: "Collaboration", color: "#60a5fa" },
  scandal: { label: "Scandal", color: "#f87171" },
};

// Era display info
const ERA_INFO: Record<Era, { label: string; range: string }> = {
  pre_romantic: { label: "Pre-Romantic", range: "1700-1789" },
  romantic: { label: "Romantic", range: "1789-1837" },
  victorian: { label: "Victorian", range: "1837-1901" },
  edwardian: { label: "Edwardian", range: "1901-1910" },
  post_1910: { label: "Post 1910", range: "1910+" },
  unknown: { label: "Unknown", range: "—" },
};

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
  nodes?: ApiNode[];
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

function toggleConnectionType(type: ConnectionType) {
  const current = [...props.filterState.connectionTypes];
  const index = current.indexOf(type);
  if (index >= 0) {
    current.splice(index, 1);
  } else {
    current.push(type);
  }
  emit("update:filter", "connectionTypes", current);
}

function isConnectionTypeActive(type: ConnectionType): boolean {
  return props.filterState.connectionTypes.includes(type);
}

function toggleEra(era: Era) {
  const current = [...props.filterState.eras];
  const index = current.indexOf(era);
  if (index >= 0) {
    current.splice(index, 1);
  } else {
    current.push(era);
  }
  emit("update:filter", "eras", current);
}

function isEraActive(era: Era): boolean {
  // Empty array means all eras are shown (no filter)
  return props.filterState.eras.length === 0 || props.filterState.eras.includes(era);
}

function toggleTier1Only() {
  emit("update:filter", "tier1Only", !props.filterState.tier1Only);
}

// Local search state synced to props
const localSearchQuery = ref(props.filterState.searchQuery);

// Watch for external changes to search query
watch(
  () => props.filterState.searchQuery,
  (newVal) => {
    localSearchQuery.value = newVal;
  }
);

// Debounced search emit
let searchTimeout: ReturnType<typeof setTimeout> | null = null;
function handleSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    emit("update:filter", "searchQuery", localSearchQuery.value);
  }, 200);
}

function handleReset() {
  localSearchQuery.value = "";
  emit("reset");
}

// All connection types for iteration (book-based + AI-discovered)
const allConnectionTypes: ConnectionType[] = [
  "publisher",
  "shared_publisher",
  "binder",
  "family",
  "friendship",
  "influence",
  "collaboration",
  "scandal",
];

// Eras to show (excluding unknown typically)
const displayEras: Era[] = ["pre_romantic", "romantic", "victorian", "edwardian", "post_1910"];
</script>

<template>
  <aside class="filter-panel" data-testid="filter-panel">
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
          v-model="localSearchQuery"
          type="text"
          class="filter-panel__input"
          placeholder="Find person..."
          @input="handleSearchInput"
        />
      </section>

      <!-- Node Types -->
      <section class="filter-panel__section">
        <h3 class="filter-panel__section-title">Node Types</h3>
        <label
          class="filter-panel__checkbox"
          data-testid="filter-authors"
          @click.prevent="toggleNodeType('showAuthors')"
        >
          <input type="checkbox" :checked="props.filterState.showAuthors" />
          <span class="filter-panel__checkbox-indicator filter-panel__checkbox-indicator--author" />
          <span>Authors</span>
          <FilterBadges
            v-if="props.nodes"
            :nodes="props.nodes"
            :filter-state="props.filterState"
            node-type="author"
          />
        </label>
        <label
          class="filter-panel__checkbox"
          data-testid="filter-publishers"
          @click.prevent="toggleNodeType('showPublishers')"
        >
          <input type="checkbox" :checked="props.filterState.showPublishers" />
          <span
            class="filter-panel__checkbox-indicator filter-panel__checkbox-indicator--publisher"
          />
          <span>Publishers</span>
          <FilterBadges
            v-if="props.nodes"
            :nodes="props.nodes"
            :filter-state="props.filterState"
            node-type="publisher"
          />
        </label>
        <label
          class="filter-panel__checkbox"
          data-testid="filter-binders"
          @click.prevent="toggleNodeType('showBinders')"
        >
          <input type="checkbox" :checked="props.filterState.showBinders" />
          <span class="filter-panel__checkbox-indicator filter-panel__checkbox-indicator--binder" />
          <span>Binders</span>
          <FilterBadges
            v-if="props.nodes"
            :nodes="props.nodes"
            :filter-state="props.filterState"
            node-type="binder"
          />
        </label>
      </section>

      <!-- Connection Types -->
      <section class="filter-panel__section">
        <h3 class="filter-panel__section-title">Connections</h3>
        <label
          v-for="ct in allConnectionTypes"
          :key="ct"
          class="filter-panel__checkbox"
          :data-testid="`filter-${ct}`"
          @click.prevent="toggleConnectionType(ct)"
        >
          <input type="checkbox" :checked="isConnectionTypeActive(ct)" />
          <span
            class="filter-panel__connection-color"
            :style="{ backgroundColor: CONNECTION_INFO[ct].color }"
          />
          <span>{{ CONNECTION_INFO[ct].label }}</span>
        </label>
      </section>

      <!-- Era Filter -->
      <section class="filter-panel__section">
        <h3 class="filter-panel__section-title">Era</h3>
        <label
          v-for="era in displayEras"
          :key="era"
          class="filter-panel__checkbox"
          :data-testid="`filter-era-${era}`"
          @click.prevent="toggleEra(era)"
        >
          <input type="checkbox" :checked="isEraActive(era)" />
          <span>{{ ERA_INFO[era].label }}</span>
          <span class="filter-panel__era-range">{{ ERA_INFO[era].range }}</span>
        </label>
      </section>

      <!-- Tier Filter -->
      <section class="filter-panel__section">
        <h3 class="filter-panel__section-title">Tier</h3>
        <label
          class="filter-panel__checkbox"
          data-testid="filter-tier1"
          @click.prevent="toggleTier1Only"
        >
          <input type="checkbox" :checked="props.filterState.tier1Only" />
          <span>Tier 1 Only</span>
        </label>
        <p class="filter-panel__help">Show only major authors and established publishers</p>
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

/* When used in mobile BottomSheet, remove fixed width and border */
.filter-panel:where(.mobile-filter-panel) {
  width: 100%;
  border-right: none;
  background: transparent;
  height: auto;
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

.filter-panel__checkbox input[type="checkbox"] {
  accent-color: var(--color-victorian-hunter-600, #2f5a4b);
}

.filter-panel__checkbox-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.filter-panel__checkbox-indicator--author {
  background-color: var(--color-victorian-hunter-600, #2f5a4b);
}

.filter-panel__checkbox-indicator--publisher {
  background-color: var(--color-victorian-gold, #c9a227);
}

.filter-panel__checkbox-indicator--binder {
  background-color: var(--color-victorian-burgundy, #722f37);
}

.filter-panel__connection-color {
  width: 16px;
  height: 3px;
  border-radius: 1px;
  flex-shrink: 0;
}

.filter-panel__era-range {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.filter-panel__help {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-top: 0.25rem;
  margin-left: 1.5rem;
}
</style>
