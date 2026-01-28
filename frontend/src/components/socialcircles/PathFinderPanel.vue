<!-- frontend/src/components/socialcircles/PathFinderPanel.vue -->
<script setup lang="ts">
/**
 * PathFinderPanel - UI for finding shortest path between two people.
 *
 * Features:
 * - Two search inputs for selecting start and end persons
 * - Find Path button (disabled until both selected)
 * - Loading state during calculation
 * - Path result display with step-by-step visualization
 * - Clear button to reset selections
 * - Graceful handling of "no path exists" scenario
 */

import { ref, computed, watch } from "vue";

import type { ApiNode, NodeId } from "@/types/socialCircles";

interface Props {
  nodes: ApiNode[];
  path: string[] | null;
  isCalculating: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "find-path", start: string, end: string): void;
  (e: "clear"): void;
}>();

// Local state for selected node IDs
const startNodeId = ref<NodeId | null>(null);
const endNodeId = ref<NodeId | null>(null);

// Search query states for filtering
const startSearchQuery = ref("");
const endSearchQuery = ref("");

// Dropdown visibility states
const showStartDropdown = ref(false);
const showEndDropdown = ref(false);

// Computed: Filter nodes by search query
const filteredStartNodes = computed(() => {
  const query = startSearchQuery.value.toLowerCase().trim();
  if (!query) return props.nodes.slice(0, 20);
  return props.nodes.filter((n) => n.name.toLowerCase().includes(query)).slice(0, 20);
});

const filteredEndNodes = computed(() => {
  const query = endSearchQuery.value.toLowerCase().trim();
  if (!query) return props.nodes.slice(0, 20);
  return props.nodes.filter((n) => n.name.toLowerCase().includes(query)).slice(0, 20);
});

// Get selected node objects
const startNode = computed(() => {
  if (!startNodeId.value) return null;
  return props.nodes.find((n) => n.id === startNodeId.value) || null;
});

const endNode = computed(() => {
  if (!endNodeId.value) return null;
  return props.nodes.find((n) => n.id === endNodeId.value) || null;
});

// Computed: Can we find a path?
const canFindPath = computed(() => {
  return (
    startNodeId.value !== null &&
    endNodeId.value !== null &&
    startNodeId.value !== endNodeId.value &&
    !props.isCalculating
  );
});

// Computed: Path nodes for display
const pathNodes = computed(() => {
  if (!props.path || props.path.length === 0) return [];
  return props.path
    .map((id) => props.nodes.find((n) => n.id === id))
    .filter((n): n is ApiNode => n !== undefined);
});

// Computed: Degrees of separation
const degreesOfSeparation = computed(() => {
  if (!props.path || props.path.length < 2) return null;
  return props.path.length - 1;
});

// Computed: Has performed a search (to show results area)
const hasSearched = computed(() => {
  return props.path !== null || props.isCalculating;
});

// Computed: No path exists (searched but empty result)
const noPathExists = computed(() => {
  return props.path !== null && props.path.length === 0;
});

// Handlers
function selectStartNode(node: ApiNode) {
  startNodeId.value = node.id;
  startSearchQuery.value = node.name;
  showStartDropdown.value = false;
}

function selectEndNode(node: ApiNode) {
  endNodeId.value = node.id;
  endSearchQuery.value = node.name;
  showEndDropdown.value = false;
}

function handleFindPath() {
  if (!canFindPath.value || !startNodeId.value || !endNodeId.value) return;
  emit("find-path", startNodeId.value, endNodeId.value);
}

function handleClear() {
  startNodeId.value = null;
  endNodeId.value = null;
  startSearchQuery.value = "";
  endSearchQuery.value = "";
  showStartDropdown.value = false;
  showEndDropdown.value = false;
  emit("clear");
}

function handleStartInputFocus() {
  showStartDropdown.value = true;
}

function handleEndInputFocus() {
  showEndDropdown.value = true;
}

function handleStartInputBlur() {
  // Delay to allow click events on dropdown items
  setTimeout(() => {
    showStartDropdown.value = false;
  }, 150);
}

function handleEndInputBlur() {
  // Delay to allow click events on dropdown items
  setTimeout(() => {
    showEndDropdown.value = false;
  }, 150);
}

// Clear selection when search query changes (user is typing new search)
watch(startSearchQuery, (newVal) => {
  if (startNode.value && newVal !== startNode.value.name) {
    startNodeId.value = null;
  }
});

watch(endSearchQuery, (newVal) => {
  if (endNode.value && newVal !== endNode.value.name) {
    endNodeId.value = null;
  }
});

// Get node type icon
function getNodeTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    author: "A",
    publisher: "P",
    binder: "B",
  };
  return icons[type] || "?";
}
</script>

<template>
  <aside class="pathfinder-panel">
    <header class="pathfinder-panel__header">
      <h2 class="pathfinder-panel__title">Degrees of Separation</h2>
    </header>

    <div class="pathfinder-panel__content">
      <!-- Start Person Input -->
      <section class="pathfinder-panel__section">
        <label class="pathfinder-panel__label" for="start-person">From</label>
        <div class="pathfinder-panel__input-wrapper">
          <input
            id="start-person"
            v-model="startSearchQuery"
            type="text"
            class="pathfinder-panel__input"
            :class="{ 'pathfinder-panel__input--selected': startNode }"
            placeholder="Search for a person..."
            autocomplete="off"
            @focus="handleStartInputFocus"
            @blur="handleStartInputBlur"
          />
          <Transition name="dropdown">
            <ul
              v-if="showStartDropdown && filteredStartNodes.length > 0"
              class="pathfinder-panel__dropdown"
            >
              <li
                v-for="node in filteredStartNodes"
                :key="node.id"
                class="pathfinder-panel__dropdown-item"
                :class="{ 'pathfinder-panel__dropdown-item--disabled': node.id === endNodeId }"
                @mousedown.prevent="node.id !== endNodeId && selectStartNode(node)"
              >
                <span
                  class="pathfinder-panel__node-badge"
                  :class="`pathfinder-panel__node-badge--${node.type}`"
                >
                  {{ getNodeTypeIcon(node.type) }}
                </span>
                <span class="pathfinder-panel__node-name">{{ node.name }}</span>
              </li>
            </ul>
          </Transition>
        </div>
      </section>

      <!-- Connector -->
      <div class="pathfinder-panel__connector">to</div>

      <!-- End Person Input -->
      <section class="pathfinder-panel__section">
        <label class="pathfinder-panel__label" for="end-person">To</label>
        <div class="pathfinder-panel__input-wrapper">
          <input
            id="end-person"
            v-model="endSearchQuery"
            type="text"
            class="pathfinder-panel__input"
            :class="{ 'pathfinder-panel__input--selected': endNode }"
            placeholder="Search for a person..."
            autocomplete="off"
            @focus="handleEndInputFocus"
            @blur="handleEndInputBlur"
          />
          <Transition name="dropdown">
            <ul
              v-if="showEndDropdown && filteredEndNodes.length > 0"
              class="pathfinder-panel__dropdown"
            >
              <li
                v-for="node in filteredEndNodes"
                :key="node.id"
                class="pathfinder-panel__dropdown-item"
                :class="{ 'pathfinder-panel__dropdown-item--disabled': node.id === startNodeId }"
                @mousedown.prevent="node.id !== startNodeId && selectEndNode(node)"
              >
                <span
                  class="pathfinder-panel__node-badge"
                  :class="`pathfinder-panel__node-badge--${node.type}`"
                >
                  {{ getNodeTypeIcon(node.type) }}
                </span>
                <span class="pathfinder-panel__node-name">{{ node.name }}</span>
              </li>
            </ul>
          </Transition>
        </div>
      </section>

      <!-- Action Buttons -->
      <div class="pathfinder-panel__actions">
        <button
          class="pathfinder-panel__button pathfinder-panel__button--primary"
          :disabled="!canFindPath"
          @click="handleFindPath"
        >
          <span v-if="isCalculating" class="pathfinder-panel__spinner"></span>
          <span v-else>Find Path</span>
        </button>
        <button
          class="pathfinder-panel__button pathfinder-panel__button--secondary"
          @click="handleClear"
        >
          Clear
        </button>
      </div>

      <!-- Results Area -->
      <section v-if="hasSearched" class="pathfinder-panel__results">
        <!-- Loading State -->
        <div v-if="isCalculating" class="pathfinder-panel__loading">
          <div class="pathfinder-panel__loading-text">Calculating path...</div>
        </div>

        <!-- No Path Exists -->
        <div v-else-if="noPathExists" class="pathfinder-panel__no-path">
          <p class="pathfinder-panel__no-path-icon">---</p>
          <p class="pathfinder-panel__no-path-message">No connection found</p>
          <p class="pathfinder-panel__no-path-detail">
            These individuals do not appear to be connected through your collection.
          </p>
        </div>

        <!-- Path Found -->
        <div v-else-if="pathNodes.length > 0" class="pathfinder-panel__path-result">
          <div class="pathfinder-panel__degrees">
            <span class="pathfinder-panel__degrees-number">{{ degreesOfSeparation }}</span>
            <span class="pathfinder-panel__degrees-label">
              {{ degreesOfSeparation === 1 ? "degree" : "degrees" }} of separation
            </span>
          </div>

          <ol class="pathfinder-panel__path-list">
            <li
              v-for="(node, index) in pathNodes"
              :key="node.id"
              class="pathfinder-panel__path-item"
            >
              <span
                class="pathfinder-panel__path-badge"
                :class="`pathfinder-panel__path-badge--${node.type}`"
              >
                {{ getNodeTypeIcon(node.type) }}
              </span>
              <span class="pathfinder-panel__path-name">{{ node.name }}</span>
              <span v-if="index < pathNodes.length - 1" class="pathfinder-panel__path-arrow"></span>
            </li>
          </ol>
        </div>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.pathfinder-panel {
  width: 280px;
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}

.pathfinder-panel__header {
  padding: 1rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.pathfinder-panel__title {
  font-size: 1rem;
  font-weight: 600;
  font-family: Georgia, serif;
  color: var(--color-victorian-hunter-700, #254a3d);
  margin: 0;
}

.pathfinder-panel__content {
  padding: 1rem;
}

.pathfinder-panel__section {
  margin-bottom: 0.75rem;
}

.pathfinder-panel__label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-bottom: 0.25rem;
}

.pathfinder-panel__input-wrapper {
  position: relative;
}

.pathfinder-panel__input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  font-size: 0.875rem;
  background: white;
  transition: border-color 0.15s ease;
}

.pathfinder-panel__input:focus {
  outline: none;
  border-color: var(--color-victorian-hunter-500, #3a6b5c);
}

.pathfinder-panel__input--selected {
  border-color: var(--color-victorian-hunter-600, #2f5a4b);
  background-color: var(--color-victorian-paper-cream, #f5f1e8);
}

.pathfinder-panel__dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 2px;
  background: white;
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  list-style: none;
  padding: 0;
  margin: 0;
}

.pathfinder-panel__dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  transition: background-color 0.1s ease;
}

.pathfinder-panel__dropdown-item:hover:not(.pathfinder-panel__dropdown-item--disabled) {
  background-color: var(--color-victorian-paper-cream, #f5f1e8);
}

.pathfinder-panel__dropdown-item--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pathfinder-panel__node-badge {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.625rem;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.pathfinder-panel__node-badge--author {
  background-color: var(--color-victorian-hunter-600, #2f5a4b);
}

.pathfinder-panel__node-badge--publisher {
  background-color: var(--color-victorian-gold, #c9a227);
}

.pathfinder-panel__node-badge--binder {
  background-color: var(--color-victorian-burgundy, #722f37);
}

.pathfinder-panel__node-name {
  font-size: 0.875rem;
  color: var(--color-victorian-ink, #2c2c2c);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pathfinder-panel__connector {
  text-align: center;
  font-size: 0.875rem;
  font-style: italic;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin: 0.5rem 0;
}

.pathfinder-panel__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.pathfinder-panel__button {
  flex: 1;
  padding: 0.625rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    opacity 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
}

.pathfinder-panel__button--primary {
  background-color: var(--color-victorian-hunter-600, #2f5a4b);
  color: white;
  border: none;
}

.pathfinder-panel__button--primary:hover:not(:disabled) {
  background-color: var(--color-victorian-hunter-700, #254a3d);
}

.pathfinder-panel__button--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pathfinder-panel__button--secondary {
  background-color: white;
  color: var(--color-victorian-ink, #2c2c2c);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.pathfinder-panel__button--secondary:hover {
  background-color: var(--color-victorian-paper-cream, #f5f1e8);
}

.pathfinder-panel__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.pathfinder-panel__results {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
}

.pathfinder-panel__loading {
  text-align: center;
  padding: 1rem;
}

.pathfinder-panel__loading-text {
  font-size: 0.875rem;
  font-style: italic;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.pathfinder-panel__no-path {
  text-align: center;
  padding: 1rem 0;
}

.pathfinder-panel__no-path-icon {
  font-size: 1.5rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin: 0 0 0.5rem;
}

.pathfinder-panel__no-path-message {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-victorian-ink, #2c2c2c);
  margin: 0 0 0.25rem;
}

.pathfinder-panel__no-path-detail {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin: 0;
  line-height: 1.4;
}

.pathfinder-panel__path-result {
  padding: 0.5rem 0;
}

.pathfinder-panel__degrees {
  text-align: center;
  margin-bottom: 1rem;
}

.pathfinder-panel__degrees-number {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  font-family: Georgia, serif;
  color: var(--color-victorian-hunter-600, #2f5a4b);
  line-height: 1;
}

.pathfinder-panel__degrees-label {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.pathfinder-panel__path-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.pathfinder-panel__path-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  position: relative;
}

.pathfinder-panel__path-badge {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.pathfinder-panel__path-badge--author {
  background-color: var(--color-victorian-hunter-600, #2f5a4b);
}

.pathfinder-panel__path-badge--publisher {
  background-color: var(--color-victorian-gold, #c9a227);
}

.pathfinder-panel__path-badge--binder {
  background-color: var(--color-victorian-burgundy, #722f37);
}

.pathfinder-panel__path-name {
  font-size: 0.875rem;
  color: var(--color-victorian-ink, #2c2c2c);
  flex: 1;
}

.pathfinder-panel__path-arrow {
  position: absolute;
  left: 11px;
  top: 100%;
  width: 2px;
  height: 12px;
  background-color: var(--color-victorian-paper-aged, #e8e1d5);
}

.pathfinder-panel__path-arrow::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: -3px;
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 6px solid var(--color-victorian-paper-aged, #e8e1d5);
}

/* Dropdown transition */
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
