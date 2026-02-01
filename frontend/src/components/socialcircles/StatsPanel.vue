<!-- frontend/src/components/socialcircles/StatsPanel.vue -->
<script setup lang="ts">
/**
 * StatsPanel - Collapsible panel displaying network statistics.
 *
 * Computes and displays:
 * - Total nodes (X authors, Y publishers, Z binders)
 * - Total connections
 * - Most connected author (with degree)
 * - Most prolific publisher (by book count)
 * - Network density percentage
 * - Average connections per node
 */

import { computed } from "vue";

import StatCard from "./StatCard.vue";
import type { ApiNode, ApiEdge, SocialCirclesMeta, NodeId } from "@/types/socialCircles";

interface Props {
  nodes: ApiNode[];
  edges: ApiEdge[];
  meta: SocialCirclesMeta;
  isCollapsed?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isCollapsed: false,
});

const emit = defineEmits<{
  toggle: [];
}>();

// Node counts by type
const nodeCounts = computed(() => {
  const counts = { author: 0, publisher: 0, binder: 0 };
  for (const node of props.nodes) {
    counts[node.type]++;
  }
  return counts;
});

const totalNodes = computed(() => props.nodes.length);
const totalConnections = computed(() => props.edges.length);

// Build adjacency map for degree calculations
const nodeDegreesMap = computed(() => {
  const degrees = new Map<NodeId, number>();
  for (const node of props.nodes) {
    degrees.set(node.id, 0);
  }
  for (const edge of props.edges) {
    degrees.set(edge.source, (degrees.get(edge.source) ?? 0) + 1);
    degrees.set(edge.target, (degrees.get(edge.target) ?? 0) + 1);
  }
  return degrees;
});

// Most connected author (by degree)
const mostConnectedAuthor = computed(() => {
  const authors = props.nodes.filter((n) => n.type === "author");
  if (authors.length === 0) return null;

  let maxDegree = 0;
  let topAuthor: ApiNode | null = null;

  for (const author of authors) {
    const degree = nodeDegreesMap.value.get(author.id) ?? 0;
    if (degree > maxDegree) {
      maxDegree = degree;
      topAuthor = author;
    }
  }

  return topAuthor ? { name: topAuthor.name, degree: maxDegree } : null;
});

// Most prolific publisher (by book count)
const mostProlificPublisher = computed(() => {
  const publishers = props.nodes.filter((n) => n.type === "publisher");
  if (publishers.length === 0) return null;

  let maxBooks = 0;
  let topPublisher: ApiNode | null = null;

  for (const publisher of publishers) {
    if (publisher.book_count > maxBooks) {
      maxBooks = publisher.book_count;
      topPublisher = publisher;
    }
  }

  return topPublisher ? { name: topPublisher.name, bookCount: maxBooks } : null;
});

// Network density: actual edges / possible edges
// For undirected graph: density = 2E / (N * (N-1))
const networkDensity = computed(() => {
  const n = props.nodes.length;
  if (n < 2) return 0;
  const maxPossibleEdges = (n * (n - 1)) / 2;
  const density = (props.edges.length / maxPossibleEdges) * 100;
  return Math.round(density * 100) / 100; // 2 decimal places
});

// Average connections per node
const avgConnectionsPerNode = computed(() => {
  if (props.nodes.length === 0) return 0;
  // Each edge contributes 2 to total degree (one for each endpoint)
  const totalDegree = props.edges.length * 2;
  const avg = totalDegree / props.nodes.length;
  return Math.round(avg * 10) / 10; // 1 decimal place
});

// Format node counts as summary string
const nodeCountSummary = computed(() => {
  const parts: string[] = [];
  if (nodeCounts.value.author > 0) {
    parts.push(`${nodeCounts.value.author} author${nodeCounts.value.author !== 1 ? "s" : ""}`);
  }
  if (nodeCounts.value.publisher > 0) {
    parts.push(
      `${nodeCounts.value.publisher} publisher${nodeCounts.value.publisher !== 1 ? "s" : ""}`
    );
  }
  if (nodeCounts.value.binder > 0) {
    parts.push(`${nodeCounts.value.binder} binder${nodeCounts.value.binder !== 1 ? "s" : ""}`);
  }
  return parts.join(", ");
});

function handleToggle() {
  emit("toggle");
}
</script>

<template>
  <div
    class="stats-panel"
    :class="{ 'stats-panel--collapsed': isCollapsed }"
    data-testid="stats-panel"
  >
    <button
      type="button"
      class="stats-panel__toggle"
      :aria-expanded="!isCollapsed"
      aria-controls="stats-panel-content"
      data-testid="stats-toggle"
      @click="handleToggle"
    >
      <span class="stats-panel__toggle-icon" data-testid="stats-toggle-icon">{{
        isCollapsed ? "+" : "-"
      }}</span>
      <span class="stats-panel__title">Network Statistics</span>
    </button>

    <Transition name="panel">
      <div
        v-show="!isCollapsed"
        id="stats-panel-content"
        class="stats-panel__content"
        data-testid="stats-content"
      >
        <!-- Primary Stats Grid -->
        <div class="stats-panel__grid" data-testid="stats-grid">
          <StatCard :value="totalNodes" label="Total Nodes" :sublabel="nodeCountSummary" />
          <StatCard :value="totalConnections" label="Connections" />
        </div>

        <!-- Secondary Stats Grid -->
        <div
          class="stats-panel__grid stats-panel__grid--secondary"
          data-testid="stats-grid-secondary"
        >
          <StatCard :value="`${networkDensity}%`" label="Network Density" />
          <StatCard :value="avgConnectionsPerNode" label="Avg. Connections" sublabel="per node" />
        </div>

        <!-- Notable Entities -->
        <div class="stats-panel__notable" data-testid="stats-notable">
          <h3 class="stats-panel__section-title">Notable Entities</h3>

          <div v-if="mostConnectedAuthor" class="stats-panel__notable-item">
            <span class="stats-panel__notable-label">Most Connected Author</span>
            <span class="stats-panel__notable-value">{{ mostConnectedAuthor.name }}</span>
            <span class="stats-panel__notable-detail"
              >({{ mostConnectedAuthor.degree }} connections)</span
            >
          </div>

          <div v-if="mostProlificPublisher" class="stats-panel__notable-item">
            <span class="stats-panel__notable-label">Most Prolific Publisher</span>
            <span class="stats-panel__notable-value">{{ mostProlificPublisher.name }}</span>
            <span class="stats-panel__notable-detail"
              >({{ mostProlificPublisher.bookCount }} books)</span
            >
          </div>

          <p
            v-if="!mostConnectedAuthor && !mostProlificPublisher"
            class="stats-panel__notable-empty"
          >
            No notable entities found.
          </p>
        </div>

        <!-- Date Range from Meta -->
        <div class="stats-panel__footer" data-testid="stats-footer">
          <span
            v-if="meta.date_range?.length === 2"
            class="stats-panel__meta"
            data-testid="stats-meta"
          >
            Collection: {{ meta.date_range[0] }} - {{ meta.date_range[1] }}
          </span>
          <span class="stats-panel__meta" data-testid="stats-meta"
            >{{ meta.total_books }} total books</span
          >
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.stats-panel {
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  overflow: hidden;
}

.stats-panel--collapsed {
  border-bottom-left-radius: 4px;
  border-bottom-right-radius: 4px;
}

.stats-panel__toggle {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--color-victorian-paper-cream, #f8f5ee);
  border: none;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  cursor: pointer;
  text-align: left;
  transition: background 150ms ease-out;
}

.stats-panel--collapsed .stats-panel__toggle {
  border-bottom: none;
}

.stats-panel__toggle:hover {
  background: var(--color-victorian-paper-aged, #e8e1d5);
}

.stats-panel__toggle:focus-visible {
  outline: 2px solid var(--color-victorian-hunter-500, #3a6b5c);
  outline-offset: -2px;
}

.stats-panel__toggle-icon {
  width: 1.25rem;
  height: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: monospace;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-victorian-hunter-600, #2f5a4b);
}

.stats-panel__title {
  font-family: "Playfair Display", "Georgia", serif;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-victorian-hunter-700, #254a3d);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stats-panel__content {
  padding: 1rem;
}

.stats-panel__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stats-panel__grid--secondary {
  margin-bottom: 1.25rem;
}

.stats-panel__section-title {
  font-family: "Playfair Display", "Georgia", serif;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin: 0 0 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.stats-panel__notable {
  margin-bottom: 1rem;
}

.stats-panel__notable-item {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 0;
  border-bottom: 1px dotted var(--color-victorian-paper-aged, #e8e1d5);
}

.stats-panel__notable-item:last-child {
  border-bottom: none;
}

.stats-panel__notable-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-bottom: 0.25rem;
}

.stats-panel__notable-value {
  font-family: "Playfair Display", "Georgia", serif;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-victorian-hunter-700, #254a3d);
  font-style: italic;
}

.stats-panel__notable-detail {
  font-family: "Georgia", serif;
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-top: 0.125rem;
}

.stats-panel__notable-empty {
  font-family: "Georgia", serif;
  font-size: 0.8125rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-style: italic;
  margin: 0;
}

.stats-panel__footer {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.stats-panel__meta {
  font-family: "Georgia", serif;
  font-size: 0.6875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-style: italic;
}

/* Panel transition */
.panel-enter-active {
  transition:
    max-height 200ms ease-out,
    opacity 200ms ease-out;
  max-height: 500px;
  overflow: hidden;
}

.panel-leave-active {
  transition:
    max-height 150ms ease-in,
    opacity 150ms ease-in;
  max-height: 500px;
  overflow: hidden;
}

.panel-enter-from,
.panel-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Responsive: single column on narrow screens */
@media (max-width: 400px) {
  .stats-panel__grid {
    grid-template-columns: 1fr;
  }
}
</style>
