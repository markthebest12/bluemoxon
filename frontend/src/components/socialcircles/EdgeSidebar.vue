<!-- frontend/src/components/socialcircles/EdgeSidebar.vue -->
<script setup lang="ts">
/**
 * EdgeSidebar - Slide-out sidebar for edge/connection details.
 * Shows relationship between two entities with shared books.
 */

import { ref, computed, watch, onUnmounted, shallowRef } from "vue";
import { useRouter } from "vue-router";
import { useFocusTrap } from "@/composables/useFocusTrap";
import { api } from "@/services/api";
import type { ApiNode, ApiEdge, NodeId, ConnectionType, NodeType } from "@/types/socialCircles";
import {
  getPlaceholderImage,
  renderStrength,
  calculateStrength,
} from "@/utils/socialCircles/formatters";
import { PANEL_ANIMATION } from "@/constants/socialCircles";
import { useClickOutside } from "@/composables/socialcircles/useClickOutside";
import { useEscapeKey } from "@/composables/socialcircles/useEscapeKey";
import { bookDetailRoute, entityProfileRoute } from "@/utils/routes";

/** Display labels for entity types */
const TYPE_LABELS: Record<NodeType, string> = {
  author: "Author",
  publisher: "Publisher",
  binder: "Bindery",
};

interface Props {
  edge: ApiEdge | null;
  nodes: readonly ApiNode[];
  isOpen: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  selectNode: [nodeId: NodeId];
  "update:pinned": [isPinned: boolean];
}>();

const router = useRouter();
const sidebarRef = ref<HTMLElement | null>(null);
const { activate, deactivate } = useFocusTrap(sidebarRef);
const isPinned = ref(false);

// Close panel when clicking outside (#1407)
useClickOutside(sidebarRef, () => {
  if (props.isOpen && !isPinned.value) {
    emit("close");
  }
});

// Source and target nodes
const sourceNode = computed(() => {
  if (!props.edge) return null;
  return props.nodes.find((n) => n.id === props.edge!.source) || null;
});

const targetNode = computed(() => {
  if (!props.edge) return null;
  return props.nodes.find((n) => n.id === props.edge!.target) || null;
});

// Connection type display
const connectionLabel = computed(() => {
  if (!props.edge) return "";
  const labels: Record<ConnectionType, string> = {
    // Book-based connections
    publisher: "Published together",
    shared_publisher: "Shared Publisher",
    binder: "Bound works",
    // AI-discovered connections
    family: "Family",
    friendship: "Friends",
    influence: "Influence",
    collaboration: "Collaborators",
    scandal: "Scandal",
  };
  return labels[props.edge.type];
});

// Strength display
const strengthDisplay = computed(() => {
  if (!props.edge) return "";
  const strength = calculateStrength(
    props.edge.shared_book_ids?.length ?? props.edge.strength ?? 0
  );
  return renderStrength(strength);
});

const sharedBookCount = computed(() => {
  return props.edge?.shared_book_ids?.length ?? 0;
});

// Evidence/narrative from AI or book-derived connections
const evidence = computed(() => props.edge?.evidence ?? null);

// AI-discovered edge types use narrative quotes; book-based types don't
const AI_TYPES = new Set(["family", "friendship", "influence", "collaboration", "scandal"]);
const isAIEdge = computed(() => !!props.edge && AI_TYPES.has(props.edge.type));

// Fetch shared books
interface BookSummary {
  id: number;
  title: string;
  year?: number;
}

const sharedBooks = ref<BookSummary[]>([]);
const isLoadingBooks = ref(false);
const fetchError = ref<string | null>(null);
const abortControllerRef = shallowRef<AbortController | null>(null);

// Check if error is a cancellation (works with both fetch AbortError and axios CancelError)
function isAbortError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  // Native fetch AbortError
  if (error.name === "AbortError") return true;
  // Axios cancellation
  if (error.name === "CanceledError" || (error as { code?: string }).code === "ERR_CANCELED")
    return true;
  return false;
}

// Shared fetch logic to avoid duplication
async function fetchSharedBooks(bookIds: number[]): Promise<void> {
  // Cancel any pending request
  if (abortControllerRef.value) {
    abortControllerRef.value.abort();
    abortControllerRef.value = null;
  }

  fetchError.value = null;
  isLoadingBooks.value = true;

  const controller = new AbortController();
  abortControllerRef.value = controller;

  try {
    const ids = bookIds.slice(0, 20).join(",");
    const response = await api.get<{ items: BookSummary[] }>(`/books?ids=${ids}&page_size=20`, {
      signal: controller.signal,
    });
    // Only update if this request wasn't aborted
    if (!controller.signal.aborted) {
      sharedBooks.value = response.data.items || [];
    }
  } catch (error) {
    // Ignore abort/cancel errors
    if (isAbortError(error)) return;
    console.error("Failed to fetch shared books:", error);
    fetchError.value = "Failed to load book details";
    sharedBooks.value = [];
  } finally {
    if (!controller.signal.aborted) {
      isLoadingBooks.value = false;
    }
  }
}

watch(
  () => ({ isOpen: props.isOpen, bookIds: props.edge?.shared_book_ids }),
  async ({ isOpen, bookIds }) => {
    if (!isOpen || !bookIds || bookIds.length === 0) {
      // Cancel pending and clear state
      if (abortControllerRef.value) {
        abortControllerRef.value.abort();
        abortControllerRef.value = null;
      }
      sharedBooks.value = [];
      fetchError.value = null;
      return;
    }
    await fetchSharedBooks(bookIds);
  },
  { immediate: true }
);

// Retry fetching books after error
function retryFetch() {
  const bookIds = props.edge?.shared_book_ids;
  if (bookIds && bookIds.length > 0) {
    void fetchSharedBooks(bookIds);
  }
}

// Navigate to book
function viewBook(bookId: number) {
  void router.push(bookDetailRoute(bookId));
}

// Entity images
function getEntityImage(node: ApiNode | null): string {
  if (!node) return "";
  return getPlaceholderImage(node.type, node.entity_id);
}

// Pin toggle
function togglePin() {
  isPinned.value = !isPinned.value;
  emit("update:pinned", isPinned.value);
}

// Global escape listener via composable
useEscapeKey(() => emit("close"));

// Focus trap management with timeout cleanup
let focusTrapTimeout: ReturnType<typeof setTimeout> | undefined;

watch(
  () => props.isOpen,
  (isOpen) => {
    // Always clear any pending timeout first to prevent race conditions
    if (focusTrapTimeout !== undefined) {
      clearTimeout(focusTrapTimeout);
      focusTrapTimeout = undefined;
    }

    if (isOpen) {
      focusTrapTimeout = setTimeout(() => activate(), PANEL_ANIMATION.duration);
    } else {
      deactivate();
    }
  }
);

onUnmounted(() => {
  if (focusTrapTimeout !== undefined) {
    clearTimeout(focusTrapTimeout);
  }
  deactivate();
  // Cancel any pending request on unmount
  if (abortControllerRef.value) {
    abortControllerRef.value.abort();
  }
});
</script>

<template>
  <Transition name="sidebar">
    <aside
      v-if="isOpen && edge && sourceNode && targetNode"
      ref="sidebarRef"
      class="edge-sidebar"
      :class="`edge-sidebar--${edge.type}`"
      role="dialog"
      aria-modal="false"
      :aria-label="`Connection between ${sourceNode.name} and ${targetNode.name}`"
    >
      <!-- Header (sticky) -->
      <header class="edge-sidebar__header">
        <div class="edge-sidebar__entities">
          <!-- Source Entity -->
          <button class="edge-sidebar__entity" @click="emit('selectNode', sourceNode.id)">
            <img
              :src="getEntityImage(sourceNode)"
              :alt="sourceNode.name"
              class="edge-sidebar__entity-image"
              loading="lazy"
            />
            <span class="edge-sidebar__entity-name">{{ sourceNode.name }}</span>
            <span class="edge-sidebar__entity-type">({{ sourceNode.type }})</span>
          </button>

          <!-- Connection indicator -->
          <div class="edge-sidebar__connection-arrow">
            {{ edge.type === "shared_publisher" ? "↔" : "→" }}
          </div>

          <!-- Target Entity -->
          <button class="edge-sidebar__entity" @click="emit('selectNode', targetNode.id)">
            <img
              :src="getEntityImage(targetNode)"
              :alt="targetNode.name"
              class="edge-sidebar__entity-image"
              loading="lazy"
            />
            <span class="edge-sidebar__entity-name">{{ targetNode.name }}</span>
            <span class="edge-sidebar__entity-type">({{ targetNode.type }})</span>
          </button>
        </div>

        <div class="edge-sidebar__actions">
          <button
            class="edge-sidebar__pin"
            :class="{ 'edge-sidebar__pin--active': isPinned }"
            :aria-pressed="isPinned"
            :aria-label="isPinned ? 'Unpin sidebar' : 'Pin sidebar'"
            :title="isPinned ? 'Click to unpin' : 'Pin to keep open'"
            @click="togglePin"
          >
            📌
          </button>
          <button class="edge-sidebar__close" aria-label="Close" @click="emit('close')">✕</button>
        </div>
      </header>

      <!-- Connection Info -->
      <section class="edge-sidebar__connection-info">
        <h3 class="edge-sidebar__connection-label">CONNECTION: {{ connectionLabel }}</h3>
        <div class="edge-sidebar__strength">
          <span class="edge-sidebar__strength-dots">{{ strengthDisplay }}</span>
          <span class="edge-sidebar__strength-count">({{ sharedBookCount }} works)</span>
        </div>
      </section>

      <!-- Evidence / Narrative (#1824) -->
      <section v-if="evidence" class="edge-sidebar__narrative">
        <p v-if="isAIEdge" class="edge-sidebar__evidence">"{{ evidence }}"</p>
        <p v-else class="edge-sidebar__evidence edge-sidebar__evidence--plain">{{ evidence }}</p>
      </section>

      <!-- Shared Books (scrollable) -->
      <section class="edge-sidebar__content">
        <h4 class="edge-sidebar__section-title">
          {{ edge.type === "binder" ? "Bound Books" : "Shared Books" }}
        </h4>

        <div v-if="isLoadingBooks" class="edge-sidebar__loading">
          <div class="edge-sidebar__skeleton-book"></div>
          <div class="edge-sidebar__skeleton-book"></div>
          <div class="edge-sidebar__skeleton-book"></div>
        </div>

        <div v-else-if="fetchError" class="edge-sidebar__error">
          <p class="edge-sidebar__error-message">{{ fetchError }}</p>
          <button class="edge-sidebar__retry-button" @click="retryFetch">Retry</button>
        </div>

        <ul v-else-if="sharedBooks.length > 0" class="edge-sidebar__book-list">
          <li v-for="book in sharedBooks" :key="book.id" class="edge-sidebar__book-item">
            <button class="edge-sidebar__book-button" @click="viewBook(book.id)">
              <span class="edge-sidebar__book-icon">📖</span>
              <span class="edge-sidebar__book-title">{{ book.title }}</span>
              <span v-if="book.year" class="edge-sidebar__book-year">({{ book.year }})</span>
            </button>
          </li>
        </ul>

        <p v-else class="edge-sidebar__empty">No shared books found in your collection.</p>
      </section>

      <!-- Footer (sticky) -->
      <footer class="edge-sidebar__footer">
        <div class="edge-sidebar__footer-group">
          <button class="edge-sidebar__view-button" @click="emit('selectNode', sourceNode.id)">
            View {{ TYPE_LABELS[sourceNode.type] || sourceNode.type }}
          </button>
          <router-link
            :to="entityProfileRoute(sourceNode.type, sourceNode.entity_id)"
            class="edge-sidebar__profile-link"
          >
            Profile &rarr;
          </router-link>
        </div>
        <div class="edge-sidebar__footer-group">
          <button class="edge-sidebar__view-button" @click="emit('selectNode', targetNode.id)">
            View {{ TYPE_LABELS[targetNode.type] || targetNode.type }}
          </button>
          <router-link
            :to="entityProfileRoute(targetNode.type, targetNode.entity_id)"
            class="edge-sidebar__profile-link"
          >
            Profile &rarr;
          </router-link>
        </div>
      </footer>
    </aside>
  </Transition>
</template>

<style scoped>
.edge-sidebar {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 35%;
  min-width: 320px;
  max-width: 500px;
  background: var(--color-sidebar-bg, #faf8f3);
  border-left: 1px solid var(--color-border, #d4cfc4);
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 3000;
}

.edge-sidebar--publisher {
  border-top: 3px solid var(--color-accent-gold, #b8860b);
}

.edge-sidebar--shared_publisher {
  border-top: 3px solid var(--color-publisher, #2c5f77);
}

.edge-sidebar--binder {
  border-top: 3px solid var(--color-binder, #8b4513);
}

.edge-sidebar__header {
  position: sticky;
  top: 0;
  padding: 16px;
  background: var(--color-sidebar-bg, #faf8f3);
  border-bottom: 1px solid var(--color-border, #d4cfc4);
  z-index: 1;
}

.edge-sidebar__entities {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.edge-sidebar__entity {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  background: none;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 150ms ease-out;
  flex: 1;
}

.edge-sidebar__entity:hover {
  background: rgba(184, 134, 11, 0.1);
}

.edge-sidebar__entity-image {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
  background: var(--color-skeleton-bg, #e8e4db);
}

.edge-sidebar__entity-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary, #2c2416);
  text-align: center;
}

.edge-sidebar__entity-type {
  font-size: 0.75rem;
  color: var(--color-text-muted, #8b8579);
}

.edge-sidebar__connection-arrow {
  font-size: 1.5rem;
  color: var(--color-text-muted, #8b8579);
}

.edge-sidebar__actions {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
}

.edge-sidebar__pin,
.edge-sidebar__close {
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--color-text-muted, #8b8579);
  cursor: pointer;
  padding: 4px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.edge-sidebar__pin:hover,
.edge-sidebar__close:hover {
  color: var(--color-text-primary, #2c2416);
}

.edge-sidebar__pin--active {
  color: var(--color-accent-gold, #b8860b);
}

.edge-sidebar__connection-info {
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #d4cfc4);
}

.edge-sidebar__connection-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-secondary, #5c5446);
  margin: 0 0 8px;
}

.edge-sidebar__strength {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edge-sidebar__strength-dots {
  font-size: 1rem;
  color: var(--color-accent-gold, #b8860b);
  letter-spacing: 2px;
}

.edge-sidebar__strength-count {
  font-size: 0.875rem;
  color: var(--color-text-muted, #8b8579);
}

.edge-sidebar__narrative {
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #d4cfc4);
}

.edge-sidebar__evidence {
  font-size: 0.875rem;
  font-style: italic;
  color: var(--color-text-secondary, #5c5446);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.edge-sidebar__evidence--plain {
  font-style: normal;
}

.edge-sidebar__content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.edge-sidebar__section-title {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #8b8579);
  margin: 0 0 12px;
}

.edge-sidebar__loading {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.edge-sidebar__skeleton-book {
  height: 48px;
  background: linear-gradient(
    90deg,
    var(--color-skeleton-bg, #e8e4db) 25%,
    #f0ede5 50%,
    var(--color-skeleton-bg, #e8e4db) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.edge-sidebar__book-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.edge-sidebar__book-item {
  margin-bottom: 4px;
}

.edge-sidebar__book-button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  min-height: 48px;
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition: background 150ms ease-out;
}

.edge-sidebar__book-button:hover {
  background: rgba(184, 134, 11, 0.1);
}

.edge-sidebar__book-button:hover .edge-sidebar__book-title {
  text-decoration: underline;
  color: var(--color-accent-gold, #b8860b);
}

.edge-sidebar__book-icon {
  font-size: 1rem;
}

.edge-sidebar__book-title {
  flex: 1;
  font-size: 0.875rem;
  color: var(--color-link, #6b4423);
  font-style: italic;
}

.edge-sidebar__book-year {
  font-size: 0.75rem;
  color: var(--color-text-muted, #8b8579);
}

.edge-sidebar__empty {
  font-size: 0.875rem;
  color: var(--color-text-muted, #8b8579);
  font-style: italic;
}

.edge-sidebar__error {
  text-align: center;
  padding: 16px;
}

.edge-sidebar__error-message {
  font-size: 0.875rem;
  color: var(--color-text-secondary, #5c5446);
  margin: 0 0 12px;
}

.edge-sidebar__retry-button {
  padding: 8px 16px;
  background: var(--color-accent-gold, #b8860b);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 150ms ease-out;
}

.edge-sidebar__retry-button:hover {
  background: var(--color-hover, #8b4513);
}

.edge-sidebar__footer {
  position: sticky;
  bottom: 0;
  padding: 16px;
  background: var(--color-sidebar-bg, #faf8f3);
  border-top: 1px solid var(--color-border, #d4cfc4);
  display: flex;
  gap: 12px;
}

.edge-sidebar__view-button {
  flex: 1;
  padding: 10px 16px;
  background: white;
  color: var(--color-text-primary, #2c2416);
  border: 1px solid var(--color-border, #d4cfc4);
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition:
    background 150ms ease-out,
    border-color 150ms ease-out;
}

.edge-sidebar__view-button:hover {
  background: var(--color-card-bg, #f5f1e8);
  border-color: var(--color-accent-gold, #b8860b);
}

/* Transitions */
.sidebar-enter-active {
  transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-leave-active {
  transition: transform 150ms cubic-bezier(0.4, 0, 1, 1);
}

.sidebar-enter-from,
.sidebar-leave-to {
  transform: translateX(100%);
}

.edge-sidebar__footer-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edge-sidebar__profile-link {
  color: var(--color-accent-gold, #b8860b);
  font-size: 0.8125rem;
  text-decoration: none;
}

.edge-sidebar__profile-link:hover {
  text-decoration: underline;
}

/* Mobile: full width */
@media (max-width: 768px) {
  .edge-sidebar {
    width: 100%;
    max-width: none;
  }
}
</style>
