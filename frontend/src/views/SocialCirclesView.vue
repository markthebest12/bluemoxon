<!-- frontend/src/views/SocialCirclesView.vue -->
<script setup lang="ts">
/**
 * Social Circles - Interactive Network Visualization
 *
 * Main view for the Victorian Social Circles feature.
 * Shows connections between authors, publishers, and binders.
 */

import { computed, onMounted, onUnmounted, provide } from 'vue';
import { useSocialCircles } from '@/composables/socialcircles';

// Components will be lazy-loaded as they're built out
import NetworkGraph from '@/components/socialcircles/NetworkGraph.vue';
import FilterPanel from '@/components/socialcircles/FilterPanel.vue';
import TimelineSlider from '@/components/socialcircles/TimelineSlider.vue';
import NodeDetailPanel from '@/components/socialcircles/NodeDetailPanel.vue';
import ZoomControls from '@/components/socialcircles/ZoomControls.vue';
import LoadingState from '@/components/socialcircles/LoadingState.vue';
import EmptyState from '@/components/socialcircles/EmptyState.vue';
import ErrorState from '@/components/socialcircles/ErrorState.vue';
import ActiveFilterPills from '@/components/socialcircles/ActiveFilterPills.vue';
import NetworkLegend from '@/components/socialcircles/NetworkLegend.vue';
import ExportMenu from '@/components/socialcircles/ExportMenu.vue';

// Initialize the main orchestrator composable
const {
  // Data
  nodes,
  edges,
  filteredNodes,
  filteredEdges,
  meta,

  // State
  loadingState,
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
  setRange,
  togglePlayback,
  setPlaybackSpeed,

  // Graph operations
  zoomIn,
  zoomOut,
  fitToView,
  getCytoscapeElements,

  // Export
  exportPng,
  exportJson,
  shareUrl,

  // Lifecycle
  initialize,
  cleanup,
} = useSocialCircles();

// Provide context to child components
provide('socialCircles', {
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
const showGraph = computed(() => !isLoading.value && !hasError.value && filteredNodes.value.length > 0);
const showEmpty = computed(() => !isLoading.value && !hasError.value && filteredNodes.value.length === 0);

// Detail panel visibility
const showDetailPanel = computed(() => selectedNode.value !== null);

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
  initialize();
}

// Lifecycle
onMounted(() => {
  initialize();
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
        <h1 class="text-2xl font-serif text-victorian-hunter-700">
          Victorian Social Circles
        </h1>
        <p class="text-sm text-victorian-ink-muted">
          Explore the connections between authors, publishers, and binders
        </p>
      </div>
      <div class="header-right">
        <ExportMenu
          @export-png="exportPng"
          @export-json="exportJson"
          @share="shareUrl"
        />
      </div>
    </header>

    <!-- Loading State -->
    <LoadingState v-if="isLoading" />

    <!-- Error State -->
    <ErrorState
      v-else-if="hasError"
      :error="error"
      @retry="handleRetry"
    />

    <!-- Empty State -->
    <EmptyState
      v-else-if="showEmpty"
      @reset-filters="resetFilters"
    />

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
          v-if="activeFilters.length > 0"
          :filters="activeFilters"
          @remove="removeFilter"
          @clear-all="resetFilters"
        />
      </aside>

      <!-- Graph Area -->
      <main class="graph-area">
        <!-- Graph viewport -->
        <div class="graph-viewport">
          <NetworkGraph
            :elements="getCytoscapeElements()"
            :selected-node="selectedNode"
            :selected-edge="selectedEdge"
            :highlighted-nodes="highlightedNodes"
            :highlighted-edges="highlightedEdges"
            @node-select="handleNodeSelect"
            @edge-select="handleEdgeSelect"
          />

          <!-- Zoom Controls (top-right of graph) -->
          <div class="zoom-controls-container">
            <ZoomControls
              @zoom-in="zoomIn"
              @zoom-out="zoomOut"
              @fit="fitToView"
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
            :state="timelineState"
            @year-change="setYear"
            @range-change="setRange"
            @toggle-play="togglePlayback"
            @speed-change="setPlaybackSpeed"
          />
        </div>
      </main>

      <!-- Detail Panel (right sidebar, slides in) -->
      <aside
        class="detail-sidebar"
        :class="{ 'detail-sidebar--open': showDetailPanel }"
      >
        <NodeDetailPanel
          v-if="showDetailPanel"
          :node="selectedNode"
          :connected-nodes="highlightedNodes"
          :connected-edges="highlightedEdges"
          @close="clearSelection"
        />
      </aside>
    </div>
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
</style>
