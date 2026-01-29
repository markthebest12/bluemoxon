<!-- frontend/src/components/socialcircles/SearchInput.vue -->
<script lang="ts">
/** Maximum number of search results shown in the dropdown. */
export const MAX_RESULTS = 10;
</script>

<script setup lang="ts">
/**
 * SearchInput - Type-ahead search input for finding people in the graph.
 *
 * Features:
 * - Debounced fuzzy search (300ms)
 * - Results grouped by type (Authors, Publishers, Binders)
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - Victorian-styled input with ornamental border
 * - Click outside closes dropdown
 */

import { ref, computed, watch, shallowRef, nextTick, onUnmounted } from "vue";
import { onClickOutside } from "@vueuse/core";

import type { ApiNode, NodeType } from "@/types/socialCircles";

// =============================================================================
// Props & Emits
// =============================================================================

interface Props {
  nodes: ApiNode[];
  modelValue: string;
  placeholder?: string;
  id?: string;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: "Search people...",
  id: "search-people",
});

const emit = defineEmits<{
  "update:modelValue": [value: string];
  select: [node: ApiNode];
}>();

// =============================================================================
// Constants
// =============================================================================

// MAX_RESULTS is exported from the companion <script> block above.
const DEBOUNCE_MS = 300;

const GROUP_LABELS: Record<NodeType, string> = {
  author: "Authors",
  publisher: "Publishers",
  binder: "Binders",
};

const GROUP_ORDER: NodeType[] = ["author", "publisher", "binder"];

// =============================================================================
// Refs
// =============================================================================

const containerRef = shallowRef<HTMLElement | null>(null);
const localQuery = ref(props.modelValue);
const debouncedQuery = ref(props.modelValue);
const isOpen = ref(false);
const activeIndex = ref(-1);

// =============================================================================
// Debouncing
// =============================================================================

let debounceTimeout: ReturnType<typeof setTimeout> | null = null;

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement;
  localQuery.value = target.value;
  emit("update:modelValue", target.value);

  // Debounce the search
  if (debounceTimeout) clearTimeout(debounceTimeout);
  debounceTimeout = setTimeout(() => {
    debouncedQuery.value = localQuery.value;
    if (debouncedQuery.value.trim()) {
      isOpen.value = true;
      activeIndex.value = -1;
    }
  }, DEBOUNCE_MS);
}

// Sync external modelValue changes
watch(
  () => props.modelValue,
  (newVal) => {
    localQuery.value = newVal;
    debouncedQuery.value = newVal;
  }
);

// Cleanup debounce timeout on unmount to prevent memory leak
onUnmounted(() => {
  if (debounceTimeout) {
    clearTimeout(debounceTimeout);
    debounceTimeout = null;
  }
});

// =============================================================================
// Search & Results
// =============================================================================

const filteredNodes = computed<ApiNode[]>(() => {
  const query = debouncedQuery.value.trim().toLowerCase();
  if (!query) return [];

  // Note: Slice is applied BEFORE grouping to limit total results.
  // This may result in uneven group representation (e.g., 8 authors, 2 publishers).
  // Trade-off: Predictable total count vs. balanced group representation.
  return props.nodes
    .filter((node) => node.name.toLowerCase().includes(query))
    .slice(0, MAX_RESULTS);
});

interface GroupedResult {
  type: NodeType;
  label: string;
  nodes: ApiNode[];
}

const groupedResults = computed<GroupedResult[]>(() => {
  const groups: GroupedResult[] = [];

  for (const type of GROUP_ORDER) {
    const nodesOfType = filteredNodes.value.filter((n) => n.type === type);
    if (nodesOfType.length > 0) {
      groups.push({
        type,
        label: GROUP_LABELS[type],
        nodes: nodesOfType,
      });
    }
  }

  return groups;
});

// Flat list for keyboard navigation
const flatResults = computed<ApiNode[]>(() => filteredNodes.value);

const hasResults = computed(() => filteredNodes.value.length > 0);
const showNoResults = computed(
  () => isOpen.value && debouncedQuery.value.trim() && !hasResults.value
);

// =============================================================================
// Click Outside
// =============================================================================

onClickOutside(containerRef, () => {
  isOpen.value = false;
});

// =============================================================================
// Keyboard Navigation
// =============================================================================

function handleKeydown(event: KeyboardEvent) {
  if (!isOpen.value && event.key !== "Escape") {
    // Open on any key that isn't escape
    if (localQuery.value.trim()) {
      isOpen.value = true;
    }
    return;
  }

  switch (event.key) {
    case "ArrowDown":
      event.preventDefault();
      if (flatResults.value.length > 0) {
        activeIndex.value = Math.min(activeIndex.value + 1, flatResults.value.length - 1);
        scrollActiveIntoView();
      }
      break;

    case "ArrowUp":
      event.preventDefault();
      if (flatResults.value.length > 0) {
        activeIndex.value = Math.max(activeIndex.value - 1, 0);
        scrollActiveIntoView();
      }
      break;

    case "Enter":
      event.preventDefault();
      if (activeIndex.value >= 0 && activeIndex.value < flatResults.value.length) {
        selectNode(flatResults.value[activeIndex.value]);
      }
      break;

    case "Escape":
      event.preventDefault();
      isOpen.value = false;
      activeIndex.value = -1;
      break;
  }
}

function scrollActiveIntoView() {
  void nextTick(() => {
    const activeEl = containerRef.value?.querySelector(".search-input__item--active");
    activeEl?.scrollIntoView({ block: "nearest" });
  });
}

// =============================================================================
// Selection
// =============================================================================

function selectNode(node: ApiNode) {
  emit("select", node);
  localQuery.value = node.name;
  emit("update:modelValue", node.name);
  isOpen.value = false;
  activeIndex.value = -1;
}

function handleFocus() {
  if (debouncedQuery.value.trim()) {
    isOpen.value = true;
  }
}

// =============================================================================
// Helpers
// =============================================================================

function getGlobalIndex(node: ApiNode): number {
  return flatResults.value.findIndex((n) => n.id === node.id);
}

function isActiveItem(node: ApiNode): boolean {
  return getGlobalIndex(node) === activeIndex.value;
}
</script>

<template>
  <div ref="containerRef" class="search-input">
    <div class="search-input__wrapper">
      <svg class="search-input__icon" viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="currentColor"
          d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 0 0 1.48-5.34c-.47-2.78-2.79-5-5.59-5.34a6.505 6.505 0 0 0-7.27 7.27c.34 2.8 2.56 5.12 5.34 5.59a6.5 6.5 0 0 0 5.34-1.48l.27.28v.79l4.25 4.25c.41.41 1.08.41 1.49 0 .41-.41.41-1.08 0-1.49L15.5 14zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
        />
      </svg>
      <input
        :id="id"
        type="text"
        class="search-input__field"
        :value="localQuery"
        :placeholder="placeholder"
        aria-label="Search people"
        autocomplete="off"
        @input="handleInput"
        @keydown="handleKeydown"
        @focus="handleFocus"
      />
    </div>

    <Transition name="dropdown">
      <div v-if="isOpen && (hasResults || showNoResults)" class="search-input__dropdown">
        <!-- Grouped Results -->
        <template v-if="hasResults">
          <div v-for="group in groupedResults" :key="group.type" class="search-input__group">
            <div class="search-input__group-header">{{ group.label }}</div>
            <button
              v-for="node in group.nodes"
              :key="node.id"
              type="button"
              class="search-input__item"
              :class="{
                'search-input__item--active': isActiveItem(node),
                [`search-input__item--${node.type}`]: true,
              }"
              @click="selectNode(node)"
              @mouseenter="activeIndex = getGlobalIndex(node)"
            >
              <span class="search-input__item-indicator" />
              <span class="search-input__item-name">{{ node.name }}</span>
              <span v-if="node.book_count" class="search-input__item-count">
                {{ node.book_count }} {{ node.book_count === 1 ? "book" : "books" }}
              </span>
            </button>
          </div>
        </template>

        <!-- No Results -->
        <div v-else-if="showNoResults" class="search-input__no-results">
          No results for "{{ debouncedQuery }}"
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.search-input {
  position: relative;
  width: 100%;
}

/* Victorian-styled input wrapper with ornamental border */
.search-input__wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  transition: border-color 0.2s ease;
}

.search-input__wrapper::before {
  content: "";
  position: absolute;
  inset: 2px;
  border: 1px solid transparent;
  border-radius: 2px;
  pointer-events: none;
  transition: border-color 0.2s ease;
}

.search-input__wrapper:focus-within {
  border-color: var(--color-victorian-hunter-500, #3a6b5c);
}

.search-input__wrapper:focus-within::before {
  border-color: var(--color-victorian-hunter-200, #a8c5bc);
}

.search-input__icon {
  width: 18px;
  height: 18px;
  margin-left: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  flex-shrink: 0;
}

.search-input__field {
  flex: 1;
  padding: 0.625rem 0.75rem;
  border: none;
  background: transparent;
  font-family: var(--font-victorian-serif, "Libre Baskerville", Georgia, serif);
  font-size: 0.875rem;
  color: var(--color-victorian-ink, #2d2d2a);
}

.search-input__field::placeholder {
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-style: italic;
}

.search-input__field:focus {
  outline: none;
}

/* Dropdown */
.search-input__dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 320px;
  overflow-y: auto;
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  box-shadow:
    0 4px 12px rgba(0, 0, 0, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.08);
  z-index: 100;
}

/* Group */
.search-input__group {
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.search-input__group:last-child {
  border-bottom: none;
}

.search-input__group-header {
  padding: 0.5rem 0.75rem;
  font-family: var(--font-victorian-serif, "Libre Baskerville", Georgia, serif);
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-ink-muted, #5c5c58);
  background-color: var(--color-victorian-paper-cream, #f5f1e8);
}

/* Result Item */
.search-input__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: none;
  border: none;
  font-family: var(--font-victorian-serif, "Libre Baskerville", Georgia, serif);
  font-size: 0.875rem;
  text-align: left;
  color: var(--color-victorian-ink, #2d2d2a);
  cursor: pointer;
  transition: background-color 0.1s ease;
}

.search-input__item:hover,
.search-input__item--active {
  background-color: var(--color-victorian-paper-cream, #f5f1e8);
}

.search-input__item-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.search-input__item--author .search-input__item-indicator {
  background-color: var(--color-victorian-hunter-600, #2f5a4b);
}

.search-input__item--publisher .search-input__item-indicator {
  background-color: var(--color-victorian-gold, #c9a227);
}

.search-input__item--binder .search-input__item-indicator {
  background-color: var(--color-victorian-burgundy, #722f37);
}

.search-input__item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-input__item-count {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  flex-shrink: 0;
}

/* No Results */
.search-input__no-results {
  padding: 1rem 0.75rem;
  font-family: var(--font-victorian-serif, "Libre Baskerville", Georgia, serif);
  font-size: 0.875rem;
  font-style: italic;
  color: var(--color-victorian-ink-muted, #5c5c58);
  text-align: center;
}

/* Dropdown Transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
