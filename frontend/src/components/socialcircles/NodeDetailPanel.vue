<!-- frontend/src/components/socialcircles/NodeDetailPanel.vue -->
<script setup lang="ts">
/**
 * NodeDetailPanel - Slide-out panel showing biographical information.
 *
 * Features:
 * - Name and dates
 * - Era and tier badges
 * - Books in collection with titles and links
 * - Connection summary
 */

import { ref, watch, computed, inject } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/services/api";
import type { Ref } from "vue";
import type { ApiNode, ApiEdge, ConnectionType } from "@/types/socialCircles";

// Injected context from parent
interface SocialCirclesContext {
  nodes: Ref<readonly ApiNode[]>;
  edges: Ref<readonly ApiEdge[]>;
}
const context = inject<SocialCirclesContext>("socialCircles");

interface Props {
  isOpen?: boolean;
  nodeId?: string;
  name?: string;
  nodeType?: "author" | "publisher" | "binder";
  birthYear?: number;
  deathYear?: number;
  era?: string;
  tier?: string;
  bookCount?: number;
  bookIds?: number[];
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  nodeId: undefined,
  name: undefined,
  nodeType: undefined,
  birthYear: undefined,
  deathYear: undefined,
  era: undefined,
  tier: undefined,
  bookCount: 0,
  bookIds: () => [],
});

const emit = defineEmits<{
  close: [];
}>();

const router = useRouter();

// Book data fetching
interface BookSummary {
  id: number;
  title: string;
  author_name?: string;
  year?: number;
}
const books = ref<BookSummary[]>([]);
const isLoadingBooks = ref(false);

// Fetch books when panel opens or bookIds change
watch(
  () => ({ isOpen: props.isOpen, bookIds: props.bookIds }),
  async ({ isOpen, bookIds }) => {
    if (!isOpen || !bookIds || bookIds.length === 0) {
      books.value = [];
      return;
    }

    isLoadingBooks.value = true;
    try {
      // Fetch books by IDs - the API supports comma-separated IDs
      const ids = bookIds.slice(0, 10).join(",");
      const response = await api.get<{ items: BookSummary[] }>(`/books?ids=${ids}&page_size=10`);
      books.value = response.data.items || [];
    } catch (error) {
      console.error("Failed to fetch books:", error);
      // Fallback to showing IDs only
      books.value = bookIds.slice(0, 10).map((id: number) => ({ id, title: `Book #${id}` }));
    } finally {
      isLoadingBooks.value = false;
    }
  },
  { immediate: true }
);

// Navigate to book detail
function viewBook(bookId: number) {
  void router.push({ name: "book-detail", params: { id: bookId } });
}

// Connection summary computed from injected context
const connectionSummary = computed(() => {
  if (!context || !props.nodeId) return [];

  const edges = context.edges.value;
  const nodes = context.nodes.value;

  // Find all edges connected to this node
  const connectedEdges = edges.filter(
    (e) => e.source === props.nodeId || e.target === props.nodeId
  );

  // Group by connection type and count
  const byType: Record<ConnectionType, { count: number; names: string[] }> = {
    publisher: { count: 0, names: [] },
    shared_publisher: { count: 0, names: [] },
    binder: { count: 0, names: [] },
  };

  connectedEdges.forEach((edge) => {
    const otherNodeId = edge.source === props.nodeId ? edge.target : edge.source;
    const otherNode = nodes.find((n) => n.id === otherNodeId);
    if (otherNode) {
      byType[edge.type].count++;
      if (byType[edge.type].names.length < 3) {
        byType[edge.type].names.push(otherNode.name);
      }
    }
  });

  // Convert to display format
  const result: Array<{ type: string; label: string; count: number; examples: string[] }> = [];

  if (byType.publisher.count > 0) {
    result.push({
      type: "publisher",
      label: props.nodeType === "publisher" ? "Published Authors" : "Publishers",
      count: byType.publisher.count,
      examples: byType.publisher.names,
    });
  }

  if (byType.shared_publisher.count > 0) {
    result.push({
      type: "shared_publisher",
      label: "Shared Publisher Connections",
      count: byType.shared_publisher.count,
      examples: byType.shared_publisher.names,
    });
  }

  if (byType.binder.count > 0) {
    result.push({
      type: "binder",
      label: "Bindery Connections",
      count: byType.binder.count,
      examples: byType.binder.names,
    });
  }

  return result;
});

function getTypeLabel(type?: string) {
  const labels: Record<string, string> = {
    author: "Author",
    publisher: "Publisher",
    binder: "Binder",
  };
  return labels[type || ""] || "Unknown";
}

function formatEra(era?: string): string {
  const labels: Record<string, string> = {
    pre_romantic: "Pre-Romantic",
    romantic: "Romantic Era",
    victorian: "Victorian",
    edwardian: "Edwardian",
    post_1910: "Post 1910",
    unknown: "Unknown Era",
  };
  return labels[era || ""] || era || "";
}
</script>

<template>
  <Transition name="slide">
    <aside v-if="isOpen" class="node-detail-panel">
      <header class="node-detail-panel__header">
        <div class="node-detail-panel__header-content">
          <span class="node-detail-panel__type">{{ getTypeLabel(nodeType) }}</span>
          <h2 class="node-detail-panel__name">{{ name || "Unknown" }}</h2>
          <p v-if="birthYear || deathYear" class="node-detail-panel__dates">
            {{ birthYear || "?" }} – {{ deathYear || "?" }}
          </p>
        </div>
        <button
          class="node-detail-panel__close"
          aria-label="Close panel"
          @click="emit('close')"
        >
          ✕
        </button>
      </header>

      <div class="node-detail-panel__content">
        <!-- Era & Tier Badges -->
        <section v-if="era || tier" class="node-detail-panel__badges">
          <span v-if="era" class="node-detail-panel__badge node-detail-panel__badge--era">
            {{ formatEra(era) }}
          </span>
          <span v-if="tier" class="node-detail-panel__badge node-detail-panel__badge--tier">
            {{ tier }}
          </span>
        </section>

        <!-- Connection Summary -->
        <section v-if="connectionSummary.length > 0" class="node-detail-panel__section">
          <h3 class="node-detail-panel__section-title">Connections</h3>
          <ul class="node-detail-panel__connections">
            <li v-for="conn in connectionSummary" :key="conn.type" class="node-detail-panel__connection">
              <span class="node-detail-panel__connection-count">{{ conn.count }}</span>
              <span class="node-detail-panel__connection-label">{{ conn.label }}</span>
              <span v-if="conn.examples.length > 0" class="node-detail-panel__connection-examples">
                {{ conn.examples.join(", ") }}{{ conn.count > conn.examples.length ? "..." : "" }}
              </span>
            </li>
          </ul>
        </section>

        <!-- Books in Collection -->
        <section class="node-detail-panel__section">
          <h3 class="node-detail-panel__section-title">
            Books in Collection
            <span class="node-detail-panel__count">({{ bookCount || 0 }})</span>
          </h3>

          <div v-if="isLoadingBooks" class="node-detail-panel__loading">
            Loading books...
          </div>

          <p v-else-if="!bookIds?.length" class="node-detail-panel__empty">
            No books linked to this {{ nodeType || "entity" }}
          </p>

          <ul v-else class="node-detail-panel__books">
            <li v-for="book in books" :key="book.id" class="node-detail-panel__book">
              <button class="node-detail-panel__book-link" @click="viewBook(book.id)">
                <span class="node-detail-panel__book-title">{{ book.title }}</span>
                <span v-if="book.year" class="node-detail-panel__book-year">
                  ({{ book.year }})
                </span>
              </button>
            </li>
            <li v-if="(bookIds?.length || 0) > 10" class="node-detail-panel__book-more">
              +{{ (bookIds?.length || 0) - 10 }} more books
            </li>
          </ul>
        </section>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.node-detail-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 100%;
  background: var(--color-victorian-paper-white, #fdfcfa);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.node-detail-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  background: linear-gradient(
    to bottom,
    var(--color-victorian-paper-cream, #f5f2e9),
    var(--color-victorian-paper-white, #fdfcfa)
  );
}

.node-detail-panel__header-content {
  flex: 1;
  min-width: 0;
}

.node-detail-panel__type {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-hunter-600, #2f5a4b);
}

.node-detail-panel__name {
  font-size: 1.25rem;
  font-weight: 600;
  font-family: Georgia, serif;
  color: var(--color-victorian-hunter-700, #254a3d);
  margin: 0.25rem 0 0;
  line-height: 1.3;
}

.node-detail-panel__dates {
  font-size: 0.875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin: 0.25rem 0 0;
}

.node-detail-panel__close {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
  opacity: 0.7;
  transition: opacity 150ms ease;
}

.node-detail-panel__close:hover {
  opacity: 1;
}

.node-detail-panel__content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
}

.node-detail-panel__badges {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.node-detail-panel__badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  border-radius: 4px;
}

.node-detail-panel__badge--era {
  background: var(--color-victorian-hunter-100, #e8f0ed);
  color: var(--color-victorian-hunter-700, #254a3d);
}

.node-detail-panel__badge--tier {
  background: var(--color-victorian-gold-100, #fdf6e3);
  color: var(--color-victorian-gold-dark, #8b6914);
}

.node-detail-panel__section {
  margin-bottom: 1.5rem;
}

.node-detail-panel__section-title {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-bottom: 0.75rem;
  display: flex;
  align-items: baseline;
  gap: 0.375rem;
}

.node-detail-panel__count {
  font-weight: 400;
  color: var(--color-victorian-ink-light, #8a8a87);
}

.node-detail-panel__connections {
  list-style: none;
  padding: 0;
  margin: 0;
}

.node-detail-panel__connection {
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
}

.node-detail-panel__connection:last-child {
  border-bottom: none;
}

.node-detail-panel__connection-count {
  display: inline-block;
  min-width: 1.5rem;
  font-weight: 600;
  color: var(--color-victorian-hunter-700, #254a3d);
}

.node-detail-panel__connection-label {
  font-size: 0.875rem;
  color: var(--color-victorian-ink, #3a3a38);
}

.node-detail-panel__connection-examples {
  display: block;
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-top: 0.25rem;
  padding-left: 1.5rem;
  font-style: italic;
}

.node-detail-panel__loading,
.node-detail-panel__empty {
  font-size: 0.875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-style: italic;
}

.node-detail-panel__books {
  list-style: none;
  padding: 0;
  margin: 0;
}

.node-detail-panel__book {
  padding: 0.375rem 0;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
}

.node-detail-panel__book:last-child {
  border-bottom: none;
}

.node-detail-panel__book-link {
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  padding: 0;
  width: 100%;
  font-size: 0.875rem;
  color: var(--color-victorian-hunter-600, #2f5a4b);
  transition: color 150ms ease;
}

.node-detail-panel__book-link:hover {
  color: var(--color-victorian-burgundy, #722f37);
}

.node-detail-panel__book-title {
  display: block;
  line-height: 1.4;
}

.node-detail-panel__book-year {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.node-detail-panel__book-more {
  padding: 0.5rem 0;
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-style: italic;
}

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: transform 300ms ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
