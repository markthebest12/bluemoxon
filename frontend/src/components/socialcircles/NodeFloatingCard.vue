<!-- frontend/src/components/socialcircles/NodeFloatingCard.vue -->
<script setup lang="ts">
/**
 * NodeFloatingCard - Floating card for entity summary.
 * Smart positioned, shows first 5 connections, links to edge details.
 */

import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useFocusTrap } from "@vueuse/integrations/useFocusTrap";
import { onClickOutside } from "@vueuse/core";
import type { ApiNode, ApiEdge, NodeId, EdgeId, ConnectionType } from "@/types/socialCircles";
import { formatTier, getPlaceholderImage } from "@/utils/socialCircles/formatters";
import {
  getBestCardPosition,
  type Position,
  type Size,
} from "@/utils/socialCircles/cardPositioning";
import { PANEL_DIMENSIONS, PANEL_ANIMATION } from "@/constants/socialCircles";

interface Props {
  node: ApiNode | null;
  nodePosition: Position | null;
  viewportSize: Size;
  edges: readonly ApiEdge[];
  nodes: readonly ApiNode[];
  isOpen: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  selectEdge: [edgeId: EdgeId];
  viewProfile: [nodeId: NodeId];
}>();

const cardRef = ref<HTMLElement | null>(null);
const { activate, deactivate } = useFocusTrap(cardRef, { immediate: false });

// Close panel when clicking outside (#1407)
onClickOutside(cardRef, () => {
  if (props.isOpen) {
    emit("close");
  }
});

// Computed position
const cardPosition = computed(() => {
  if (!props.nodePosition || !props.isOpen) return null;

  const cardSize: Size = {
    width: PANEL_DIMENSIONS.card.width,
    height: PANEL_DIMENSIONS.card.maxHeight,
  };

  return getBestCardPosition(
    props.nodePosition,
    cardSize,
    props.viewportSize,
    PANEL_DIMENSIONS.card.margin
  );
});

// Tier display
const tierDisplay = computed(() => {
  return props.node?.tier ? formatTier(props.node.tier) : null;
});

// Placeholder image
const entityImage = computed(() => {
  if (!props.node) return "";
  return getPlaceholderImage(props.node.type, props.node.entity_id);
});

// Connections (first 5)
interface ConnectionItem {
  edgeId: EdgeId;
  nodeId: NodeId;
  nodeName: string;
  nodeType: string;
  connectionType: ConnectionType;
}

const connections = computed((): ConnectionItem[] => {
  if (!props.node) return [];

  const result: ConnectionItem[] = [];
  const nodeId = props.node.id;

  for (const edge of props.edges) {
    if (result.length >= 5) break;

    let otherNodeId: NodeId | null = null;
    if (edge.source === nodeId) {
      otherNodeId = edge.target as NodeId;
    } else if (edge.target === nodeId) {
      otherNodeId = edge.source as NodeId;
    }

    if (otherNodeId) {
      const otherNode = props.nodes.find((n) => n.id === otherNodeId);
      if (otherNode) {
        result.push({
          edgeId: edge.id,
          nodeId: otherNodeId,
          nodeName: otherNode.name,
          nodeType: otherNode.type,
          connectionType: edge.type,
        });
      }
    }
  }

  return result;
});

const totalConnections = computed(() => {
  if (!props.node) return 0;
  return props.edges.filter((e) => e.source === props.node!.id || e.target === props.node!.id)
    .length;
});

const remainingConnections = computed(() => {
  return Math.max(0, totalConnections.value - connections.value.length);
});

// Connection type icons
function getConnectionIcon(type: ConnectionType): string {
  const icons: Record<ConnectionType, string> = {
    publisher: "📚",
    shared_publisher: "🤝",
    binder: "🪡",
  };
  return icons[type] || "→";
}

// Keyboard handling
function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    emit("close");
  }
}

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

// Global escape listener
onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
  if (focusTrapTimeout !== undefined) {
    clearTimeout(focusTrapTimeout);
  }
  deactivate();
});
</script>

<template>
  <Transition name="card">
    <div
      v-if="isOpen && node && cardPosition"
      ref="cardRef"
      class="node-floating-card"
      :class="`node-floating-card--${node.type}`"
      :style="{
        left: `${cardPosition.position.x}px`,
        top: `${cardPosition.position.y}px`,
      }"
      role="dialog"
      aria-modal="false"
      :aria-label="`Details for ${node.name}`"
    >
      <!-- Header -->
      <header class="node-floating-card__header">
        <img
          :src="entityImage"
          :alt="`Portrait of ${node.name}`"
          class="node-floating-card__image"
          loading="lazy"
        />
        <div class="node-floating-card__info">
          <h3 class="node-floating-card__name">{{ node.name }}</h3>
          <div v-if="tierDisplay" class="node-floating-card__tier" :title="tierDisplay.tooltip">
            <span class="sr-only">{{ tierDisplay.tooltip }}</span>
            <span aria-hidden="true"
              >{{ "★".repeat(tierDisplay.stars) }}{{ "☆".repeat(3 - tierDisplay.stars) }}</span
            >
          </div>
          <p v-if="node.birth_year || node.death_year" class="node-floating-card__dates">
            {{ node.birth_year || "?" }} – {{ node.death_year || "?" }}
          </p>
          <p v-if="node.era" class="node-floating-card__era">
            {{ node.era.replace("_", " ") }}
          </p>
        </div>
        <button class="node-floating-card__close" aria-label="Close" @click="emit('close')">
          ✕
        </button>
      </header>

      <!-- Stats -->
      <div class="node-floating-card__stats">
        <span>{{ node.book_count }} books</span>
        <span>·</span>
        <span>{{ totalConnections }} connections</span>
      </div>

      <!-- Connections -->
      <section v-if="connections.length > 0" class="node-floating-card__connections">
        <h4 class="node-floating-card__section-title">
          Connections
          <span v-if="remainingConnections > 0"
            >(showing {{ connections.length }} of {{ totalConnections }})</span
          >
        </h4>
        <ul class="node-floating-card__connection-list">
          <li
            v-for="conn in connections"
            :key="conn.edgeId"
            class="node-floating-card__connection-item"
          >
            <button
              class="node-floating-card__connection-button"
              @click="emit('selectEdge', conn.edgeId)"
            >
              <span class="node-floating-card__connection-icon">{{
                getConnectionIcon(conn.connectionType)
              }}</span>
              <span class="node-floating-card__connection-name">{{ conn.nodeName }}</span>
              <span class="node-floating-card__connection-type">({{ conn.nodeType }})</span>
            </button>
          </li>
        </ul>
        <button
          v-if="remainingConnections > 0"
          class="node-floating-card__more-link"
          @click="emit('viewProfile', node.id)"
        >
          View {{ remainingConnections }} more in full profile →
        </button>
      </section>

      <!-- Empty connections -->
      <section v-else class="node-floating-card__empty">
        <p>No connections found in your collection.</p>
      </section>

      <!-- Footer -->
      <footer class="node-floating-card__footer">
        <button class="node-floating-card__profile-button" @click="emit('viewProfile', node.id)">
          View Full Profile →
        </button>
      </footer>
    </div>
  </Transition>
</template>

<style scoped>
.node-floating-card {
  position: absolute;
  width: 280px;
  max-height: 400px;
  background: var(--color-card-bg, #f5f1e8);
  border: 1px solid var(--color-border, #d4cfc4);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2000;
}

.node-floating-card--author {
  border-top: 3px solid var(--color-author, #7b4b94);
}

.node-floating-card--publisher {
  border-top: 3px solid var(--color-publisher, #2c5f77);
}

.node-floating-card--binder {
  border-top: 3px solid var(--color-binder, #8b4513);
}

.node-floating-card__header {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #d4cfc4);
}

.node-floating-card__image {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
  background: var(--color-skeleton-bg, #e8e4db);
}

.node-floating-card__info {
  flex: 1;
  min-width: 0;
}

.node-floating-card__name {
  font-size: 1rem;
  font-weight: 600;
  font-family: Georgia, serif;
  color: var(--color-text-primary, #2c2416);
  margin: 0;
  line-height: 1.3;
}

.node-floating-card__tier {
  color: var(--color-accent-gold, #b8860b);
  font-size: 0.875rem;
  margin-top: 2px;
}

.node-floating-card__dates,
.node-floating-card__era {
  font-size: 0.75rem;
  color: var(--color-text-secondary, #5c5446);
  margin: 2px 0 0;
}

.node-floating-card__close {
  position: absolute;
  top: 12px;
  right: 12px;
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

.node-floating-card__close:hover {
  color: var(--color-text-primary, #2c2416);
}

.node-floating-card__stats {
  padding: 8px 16px;
  font-size: 0.75rem;
  color: var(--color-text-secondary, #5c5446);
  display: flex;
  gap: 6px;
  border-bottom: 1px solid var(--color-border, #d4cfc4);
}

.node-floating-card__connections {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.node-floating-card__section-title {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #8b8579);
  margin: 0 0 8px;
}

.node-floating-card__connection-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.node-floating-card__connection-item {
  margin-bottom: 4px;
}

.node-floating-card__connection-button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px;
  min-height: 48px;
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition:
    background 150ms ease-out,
    transform 150ms ease-out;
}

.node-floating-card__connection-button:hover {
  background: rgba(184, 134, 11, 0.1);
  transform: translateX(4px);
}

.node-floating-card__connection-icon {
  font-size: 1rem;
}

.node-floating-card__connection-name {
  flex: 1;
  font-size: 0.875rem;
  color: var(--color-text-primary, #2c2416);
}

.node-floating-card__connection-type {
  font-size: 0.75rem;
  color: var(--color-text-muted, #8b8579);
}

.node-floating-card__more-link {
  display: block;
  margin-top: 8px;
  padding: 4px 0;
  background: none;
  border: none;
  font-size: 0.75rem;
  color: var(--color-link, #6b4423);
  cursor: pointer;
  text-decoration: underline;
}

.node-floating-card__more-link:hover {
  color: var(--color-hover, #8b4513);
}

.node-floating-card__empty {
  padding: 16px;
  font-size: 0.875rem;
  color: var(--color-text-muted, #8b8579);
  font-style: italic;
}

.node-floating-card__footer {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border, #d4cfc4);
}

.node-floating-card__profile-button {
  width: 100%;
  padding: 10px 16px;
  background: var(--color-accent-gold, #b8860b);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background 150ms ease-out,
    transform 150ms ease-out;
}

.node-floating-card__profile-button:hover {
  background: var(--color-hover, #8b4513);
  transform: translateY(-1px);
}

/* Transitions */
.card-enter-active {
  transition:
    transform 200ms cubic-bezier(0.4, 0, 0.2, 1),
    opacity 200ms ease-out;
}

.card-leave-active {
  transition:
    transform 150ms cubic-bezier(0.4, 0, 1, 1),
    opacity 150ms ease-in;
}

.card-enter-from,
.card-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* Screen reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
