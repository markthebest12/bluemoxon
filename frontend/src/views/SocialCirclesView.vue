<!-- frontend/src/views/SocialCirclesView.vue -->
<script setup lang="ts">
/**
 * Social Circles - Interactive Network Visualization
 *
 * Main view for the Victorian Social Circles feature.
 * Shows connections between authors, publishers, and binders.
 */

import { computed, onMounted, onUnmounted, provide, ref } from "vue";
import { useSocialCircles } from "@/composables/socialcircles";
import type { ConnectionType } from "@/types/socialCircles";

// Components will be lazy-loaded as they're built out
import NetworkGraph from "@/components/socialcircles/NetworkGraph.vue";
import FilterPanel from "@/components/socialcircles/FilterPanel.vue";
import TimelineSlider from "@/components/socialcircles/TimelineSlider.vue";
import NodeDetailPanel from "@/components/socialcircles/NodeDetailPanel.vue";
import ZoomControls from "@/components/socialcircles/ZoomControls.vue";
import LoadingState from "@/components/socialcircles/LoadingState.vue";
import EmptyState from "@/components/socialcircles/EmptyState.vue";
import ErrorState from "@/components/socialcircles/ErrorState.vue";
import ActiveFilterPills from "@/components/socialcircles/ActiveFilterPills.vue";
import NetworkLegend from "@/components/socialcircles/NetworkLegend.vue";
import ExportMenu from "@/components/socialcircles/ExportMenu.vue";
import ConnectionTooltip from "@/components/socialcircles/ConnectionTooltip.vue";

// Initialize the main orchestrator composable
const {
  // Data
  nodes,
  edges,
  filteredNodes,
  filteredEdges,
  meta,

  // State
  error,
  isLoading,
  hasError,

  // Filters
  filterState,
  activeFilters,
  applyFilter,
  resetFilters,
  removeFilter,

  // Selection
  selectedNode,
  selectedEdge,
  highlightedNodes,
  highlightedEdges,
  selectNode,
  selectEdge,
  clearSelection,

  // Timeline
  timelineState,
  setYear,
  togglePlayback,

  // Graph operations
  getCytoscapeElements,

  // Export
  exportPng,
  exportJson,
  shareUrl,

  // Cytoscape instance setter
  setCytoscapeInstance,

  // Lifecycle
  initialize,
  cleanup,
} = useSocialCircles();

// NetworkGraph ref for zoom controls and export
const networkGraphRef = ref<InstanceType<typeof NetworkGraph> | null>(null);

// Toast state for share feedback
const showToast = ref(false);
const toastMessage = ref("");

function showToastMessage(message: string) {
  toastMessage.value = message;
  showToast.value = true;
  setTimeout(() => {
    showToast.value = false;
  }, 3000);
}

// Tooltip state for edge hover - store only the data we need, not the readonly ref
interface HoveredEdgeData {
  id: string;
  source: string;
  target: string;
  type: ConnectionType;
  strength: number;
  evidence?: string;
  shared_book_ids?: number[];
  start_year?: number;
  end_year?: number;
}
const hoveredEdge = ref<HoveredEdgeData | null>(null);
const tooltipPosition = ref({ x: 0, y: 0 });

function handleEdgeHover(edgeId: string | null, event: MouseEvent | null) {
  if (edgeId && event) {
    // Find the edge data
    const edge = edges.value.find((e) => e.id === edgeId);
    if (edge) {
      // Convert to mutable object to avoid readonly type issues
      hoveredEdge.value = {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        strength: edge.strength,
        evidence: edge.evidence,
        shared_book_ids: edge.shared_book_ids ? [...edge.shared_book_ids] : undefined,
        start_year: edge.start_year,
        end_year: edge.end_year,
      };
      tooltipPosition.value = { x: event.clientX, y: event.clientY };
    } else {
      hoveredEdge.value = null;
    }
  } else {
    hoveredEdge.value = null;
  }
}

// Get node name by ID for tooltip display
function getNodeName(nodeId: string): string {
  const node = nodes.value.find((n) => n.id === nodeId);
  return node?.name ?? nodeId;
}

// Track mouse movement for tooltip positioning while hovering edge
function handleGraphMouseMove(event: MouseEvent) {
  if (hoveredEdge.value) {
    tooltipPosition.value = { x: event.clientX, y: event.clientY };
  }
}

function handleZoomIn() {
  networkGraphRef.value?.zoomIn();
}

function handleZoomOut() {
  networkGraphRef.value?.zoomOut();
}

function handleFitToView() {
  networkGraphRef.value?.fitToView();
}

// Export handlers with feedback
async function handleExportPng() {
  // Get cytoscape instance from NetworkGraph
  const cy = networkGraphRef.value?.getCytoscape();
  if (cy) {
    setCytoscapeInstance(cy);
  }
  const result = await exportPng();
  if (result.success) {
    showToastMessage("PNG exported successfully");
  } else {
    showToastMessage(result.error || "Export failed");
  }
}

function handleExportJson() {
  exportJson();
  showToastMessage("JSON exported successfully");
}

async function handleShare() {
  const result = await shareUrl();
  if (result.success) {
    if (result.method === "clipboard") {
      showToastMessage("Link copied to clipboard");
    }
    // Native share doesn't need a toast - the OS handles it
  } else if (result.error !== "Cancelled") {
    showToastMessage(result.error || "Share failed");
  }
}

// Provide context to child components
provide("socialCircles", {
  nodes,
  edges,
  filteredNodes,
  filteredEdges,
  meta,
  filterState,
  timelineState,
  selectedNode,
  selectedEdge,
  highlightedNodes,
  highlightedEdges,
});

// Computed states
const showGraph = computed(
  () => !isLoading.value && !hasError.value && filteredNodes.value.length > 0
);
const showEmpty = computed(
  () => !isLoading.value && !hasError.value && filteredNodes.value.length === 0
);

// Detail panel visibility
const showDetailPanel = computed(() => selectedNode.value !== null);

// Cytoscape elements - computed to avoid re-layout on unrelated re-renders
const cytoscapeElements = computed(() => getCytoscapeElements());

// Transform activeFilters to match component interface (value must be string)
const filterPills = computed(() =>
  activeFilters.value.map((f) => ({
    key: f.key,
    label: f.label,
    value: String(f.value),
  }))
);

// Handle node selection from graph
function handleNodeSelect(nodeId: string | null) {
  if (nodeId) {
    selectNode(nodeId);
  } else {
    clearSelection();
  }
}

// Handle edge selection from graph
function handleEdgeSelect(edgeId: string | null) {
  if (edgeId) {
    selectEdge(edgeId);
  } else {
    clearSelection();
  }
}

// Handle retry after error
function handleRetry() {
  initialize().catch(console.error);
}

// Lifecycle
onMounted(() => {
  initialize().catch(console.error);
});

onUnmounted(() => {
  cleanup();
});
</script>

<template>
  <div class="social-circles-view">
    <!-- Header -->
    <header class="social-circles-header">
      <div class="header-left">
        <h1 class="text-2xl font-serif text-victorian-hunter-700">Victorian Social Circles</h1>
        <p class="text-sm text-victorian-ink-muted">
          Explore the connections between authors, publishers, and binders
        </p>
      </div>
      <div class="header-right">
        <ExportMenu
          @export-png="handleExportPng"
          @export-json="handleExportJson"
          @share="handleShare"
        />
      </div>
    </header>

    <!-- Loading State -->
    <LoadingState v-if="isLoading" />

    <!-- Error State -->
    <ErrorState
      v-else-if="hasError"
      :message="error?.message"
      :retryable="error?.retryable"
      @retry="handleRetry"
    />

    <!-- Empty State -->
    <EmptyState v-else-if="showEmpty" @reset-filters="resetFilters" />

    <!-- Main Content -->
    <div v-else-if="showGraph" class="social-circles-content">
      <!-- Filter Panel (left sidebar) -->
      <aside class="filter-sidebar">
        <FilterPanel
          :filter-state="filterState"
          @update:filter="applyFilter"
          @reset="resetFilters"
        />

        <!-- Active Filter Pills -->
        <ActiveFilterPills
          v-if="filterPills.length > 0"
          :filters="filterPills"
          @remove="removeFilter"
          @clear-all="resetFilters"
        />
      </aside>

      <!-- Graph Area -->
      <main class="graph-area">
        <!-- Graph viewport -->
        <div class="graph-viewport" @mousemove="handleGraphMouseMove">
          <NetworkGraph
            ref="networkGraphRef"
            :elements="cytoscapeElements"
            :selected-node="selectedNode"
            :selected-edge="selectedEdge"
            :highlighted-nodes="highlightedNodes"
            :highlighted-edges="highlightedEdges"
            @node-select="handleNodeSelect"
            @edge-select="handleEdgeSelect"
            @edge-hover="handleEdgeHover"
          />

          <!-- Zoom Controls (top-right of graph) -->
          <div class="zoom-controls-container">
            <ZoomControls
              @zoom-in="handleZoomIn"
              @zoom-out="handleZoomOut"
              @fit="handleFitToView"
            />
          </div>

          <!-- Legend (bottom-right of graph) -->
          <div class="legend-container">
            <NetworkLegend />
          </div>
        </div>

        <!-- Timeline (below graph) -->
        <div class="timeline-area">
          <TimelineSlider
            :min-year="timelineState.minYear"
            :max-year="timelineState.maxYear"
            :current-year="timelineState.currentYear"
            :mode="timelineState.mode"
            :is-playing="timelineState.isPlaying"
            @year-change="setYear"
            @mode-change="
              () => {
                /* TODO: wire mode change */
              }
            "
            @play="togglePlayback"
            @pause="togglePlayback"
          />
        </div>
      </main>

      <!-- Detail Panel (right sidebar, slides in) -->
      <aside class="detail-sidebar" :class="{ 'detail-sidebar--open': showDetailPanel }">
        <NodeDetailPanel
          v-if="selectedNode"
          :is-open="showDetailPanel"
          :node-id="selectedNode?.id"
          :name="selectedNode?.name"
          :node-type="selectedNode?.type"
          :birth-year="selectedNode?.birth_year"
          :death-year="selectedNode?.death_year"
          :era="selectedNode?.era"
          :tier="selectedNode?.tier ?? undefined"
          :book-count="selectedNode?.book_count"
          :book-ids="selectedNode?.book_ids ? [...selectedNode.book_ids] : undefined"
          @close="clearSelection"
        />
      </aside>

      <!-- Connection Tooltip (edge hover) -->
      <ConnectionTooltip
        :visible="hoveredEdge !== null"
        :x="tooltipPosition.x"
        :y="tooltipPosition.y"
        :source-name="hoveredEdge ? getNodeName(hoveredEdge.source) : ''"
        :target-name="hoveredEdge ? getNodeName(hoveredEdge.target) : ''"
        :connection-type="(hoveredEdge?.type ?? 'publisher') as ConnectionType"
        :strength="hoveredEdge?.strength"
        :evidence="hoveredEdge?.evidence"
        :start-year="hoveredEdge?.start_year"
        :end-year="hoveredEdge?.end_year"
        :shared-book-count="hoveredEdge?.shared_book_ids?.length"
      />
    </div>

    <!-- Toast notification -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="showToast" class="social-circles-toast">
          {{ toastMessage }}
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.social-circles-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--color-victorian-paper-cream, #f5f2e9);
  overflow: hidden;
}

.social-circles-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.social-circles-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.filter-sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  overflow-y: auto;
}

.graph-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.graph-viewport {
  flex: 1;
  position: relative;
  overflow: hidden;
  /* Reserve space to prevent CLS during graph loading */
  min-height: 500px;
}

.zoom-controls-container {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 10;
}

.legend-container {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  z-index: 10;
}

.timeline-area {
  flex-shrink: 0;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  background-color: var(--color-victorian-paper-white, #fdfcfa);
}

.detail-sidebar {
  width: 0;
  flex-shrink: 0;
  overflow: hidden;
  transition: width 0.3s ease;
  border-left: 1px solid transparent;
  background-color: var(--color-victorian-paper-white, #fdfcfa);
}

.detail-sidebar--open {
  width: 360px;
  border-left-color: var(--color-victorian-paper-aged, #e8e4d9);
  overflow-y: auto;
}

/* Responsive adjustments */
@media (max-width: 1024px) {
  .filter-sidebar {
    width: 240px;
  }

  .detail-sidebar--open {
    width: 320px;
  }
}

@media (max-width: 768px) {
  .social-circles-content {
    flex-direction: column;
  }

  .filter-sidebar {
    width: 100%;
    max-height: 200px;
    border-right: none;
    border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  }

  .detail-sidebar--open {
    position: fixed;
    top: 0;
    right: 0;
    height: 100vh;
    width: 100%;
    max-width: 400px;
    z-index: 100;
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
  }
}

/* Toast notification */
.social-circles-toast {
  position: fixed;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.25rem;
  background-color: var(--color-victorian-hunter-700, #254a3d);
  color: white;
  border-radius: 6px;
  font-size: 0.875rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 1000;
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 200ms ease,
    transform 200ms ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(0.5rem);
}
</style>
