<!-- frontend/src/components/socialcircles/SearchResults.vue -->
<script setup lang="ts">
/**
 * SearchResults - Dropdown showing grouped search results.
 *
 * Features:
 * - Groups results by node type (Authors, Publishers, Binders)
 * - Highlights matching text in names
 * - Shows node metadata (birth year, book count)
 * - Keyboard navigable with active index highlighting
 * - Click or Enter selects item
 * - Mouseover updates active index via hover emit
 */

import { computed } from "vue";
import type { ApiNode, NodeType } from "@/types/socialCircles";

// Node type display configuration
const NODE_TYPE_INFO: Record<NodeType, { label: string; pluralLabel: string; color: string }> = {
  author: {
    label: "Author",
    pluralLabel: "Authors",
    color: "var(--color-victorian-hunter-600, #2f5a4b)",
  },
  publisher: {
    label: "Publisher",
    pluralLabel: "Publishers",
    color: "var(--color-victorian-gold, #c9a227)",
  },
  binder: {
    label: "Binder",
    pluralLabel: "Binders",
    color: "var(--color-victorian-burgundy, #722f37)",
  },
};

// Order for displaying groups
const NODE_TYPE_ORDER: NodeType[] = ["author", "publisher", "binder"];

interface Props {
  results: ApiNode[];
  activeIndex: number;
  query: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  select: [node: ApiNode];
  hover: [index: number];
}>();

// Grouped results by node type
interface GroupedResult {
  type: NodeType;
  label: string;
  color: string;
  nodes: Array<{ node: ApiNode; flatIndex: number }>;
}

const groupedResults = computed((): GroupedResult[] => {
  const groups: Record<NodeType, ApiNode[]> = {
    author: [],
    publisher: [],
    binder: [],
  };

  // Separate nodes by type
  for (const node of props.results) {
    groups[node.type].push(node);
  }

  // Build grouped results with flat indices for keyboard navigation
  const result: GroupedResult[] = [];
  let flatIndex = 0;

  for (const type of NODE_TYPE_ORDER) {
    const nodes = groups[type];
    if (nodes.length > 0) {
      const info = NODE_TYPE_INFO[type];
      result.push({
        type,
        label: info.pluralLabel,
        color: info.color,
        nodes: nodes.map((node) => ({
          node,
          flatIndex: flatIndex++,
        })),
      });
    }
  }

  return result;
});

// Check if there are any results
const hasResults = computed(() => props.results.length > 0);

/**
 * Highlights matching query text within a name.
 * Returns HTML with matched portions wrapped in <mark>.
 */
function highlightMatch(name: string): string {
  if (!props.query.trim()) {
    return escapeHtml(name);
  }

  const query = props.query.trim();
  const regex = new RegExp(`(${escapeRegex(query)})`, "gi");
  const parts = name.split(regex);

  return parts
    .map((part) => {
      if (part.toLowerCase() === query.toLowerCase()) {
        return `<mark class="search-results__highlight">${escapeHtml(part)}</mark>`;
      }
      return escapeHtml(part);
    })
    .join("");
}

/**
 * Escapes HTML special characters to prevent XSS.
 * Uses string replacement for better performance (avoids DOM allocation).
 */
const HTML_ESCAPE_MAP: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => HTML_ESCAPE_MAP[char]);
}

/**
 * Escapes regex special characters.
 */
function escapeRegex(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Formats metadata line for a node.
 */
function formatMetadata(node: ApiNode): string {
  const parts: string[] = [];

  // Birth year for authors
  if (node.type === "author" && node.birth_year) {
    parts.push(`b. ${node.birth_year}`);
  }

  // Founded year for publishers/binders
  if ((node.type === "publisher" || node.type === "binder") && node.founded_year) {
    parts.push(`est. ${node.founded_year}`);
  }

  // Book count
  const bookLabel = node.book_count === 1 ? "book" : "books";
  parts.push(`${node.book_count} ${bookLabel}`);

  return parts.join(" · ");
}

function handleSelect(node: ApiNode) {
  emit("select", node);
}

function handleHover(index: number) {
  emit("hover", index);
}

function handleKeydown(event: KeyboardEvent, node: ApiNode) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    handleSelect(node);
  }
}
</script>

<template>
  <div class="search-results" role="listbox" aria-label="Search results">
    <template v-if="hasResults">
      <div v-for="group in groupedResults" :key="group.type" class="search-results__group">
        <!-- Group header -->
        <div class="search-results__group-header">
          <span class="search-results__group-indicator" :style="{ backgroundColor: group.color }" />
          <span class="search-results__group-label">{{ group.label }}</span>
          <span class="search-results__group-count">({{ group.nodes.length }})</span>
        </div>

        <!-- Group items -->
        <div
          v-for="{ node, flatIndex } in group.nodes"
          :key="node.id"
          class="search-results__item"
          :class="{ 'search-results__item--active': flatIndex === activeIndex }"
          role="option"
          :aria-selected="flatIndex === activeIndex"
          tabindex="0"
          @click="handleSelect(node)"
          @mouseover="handleHover(flatIndex)"
          @keydown="handleKeydown($event, node)"
        >
          <span class="search-results__item-indicator" :style="{ backgroundColor: group.color }" />
          <div class="search-results__item-content">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span class="search-results__item-name" v-html="highlightMatch(node.name)" />
            <span class="search-results__item-meta">{{ formatMetadata(node) }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- Empty state -->
    <div v-else class="search-results__empty">
      <span class="search-results__empty-text">No results found</span>
    </div>
  </div>
</template>

<style scoped>
.search-results {
  max-height: 320px;
  overflow-y: auto;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.search-results__group {
  padding: 0.5rem 0;
}

.search-results__group:not(:last-child) {
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.search-results__group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.search-results__group-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.search-results__group-label {
  flex: 1;
}

.search-results__group-count {
  font-weight: normal;
}

.search-results__item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.search-results__item:hover,
.search-results__item--active {
  background: var(--color-victorian-paper-cream, #f5f1e8);
}

.search-results__item--active {
  background: var(--color-victorian-paper-warm, #ede8dd);
}

.search-results__item:focus {
  outline: none;
  background: var(--color-victorian-paper-warm, #ede8dd);
}

.search-results__item:focus-visible {
  outline: 2px solid var(--color-victorian-hunter-500, #3a6b5c);
  outline-offset: -2px;
}

.search-results__item-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 0.375rem;
}

.search-results__item-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.search-results__item-name {
  font-size: 0.875rem;
  font-family: Georgia, serif;
  color: var(--color-victorian-ink-dark, #2c2416);
  line-height: 1.3;
}

.search-results__item-meta {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

/* Highlight styling (applied via v-html) */
.search-results :deep(.search-results__highlight) {
  background-color: var(--color-victorian-gold-light, #f5e6b3);
  color: inherit;
  padding: 0 0.125rem;
  border-radius: 2px;
}

.search-results__empty {
  padding: 1.5rem 0.75rem;
  text-align: center;
}

.search-results__empty-text {
  font-size: 0.875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-style: italic;
}
</style>
