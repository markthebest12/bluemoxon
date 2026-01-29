<!-- frontend/src/views/SocialCirclesView.vue -->
<script setup lang="ts">
/**
 * Social Circles - Interactive Network Visualization
 *
 * Main view for the Victorian Social Circles feature.
 * Shows connections between authors, publishers, and binders.
 */

import { computed, onMounted, onUnmounted, provide, ref } from "vue";
import { useWindowSize } from "@vueuse/core";
// Note: useRouter from "vue-router" will be needed when entity-detail route is implemented
import {
  useAnalytics,
  useSocialCircles,
  useNetworkKeyboard,
  usePathFinder,
  useFindSimilar,
  useMobile,
  type SimilarNode,
} from "@/composables/socialcircles";
import {
  DEFAULT_TIMELINE_STATE,
  type ConnectionType,
  type FilterState,
  type LayoutMode,
  type NodeId,
  type EdgeId,
  type ApiNode,
  type ApiEdge,
  type SocialCirclesMeta,
} from "@/types/socialCircles";
import type { Position } from "@/utils/socialCircles/cardPositioning";

// Components
import NetworkGraph from "@/components/socialcircles/NetworkGraph.vue";
import FilterPanel from "@/components/socialcircles/FilterPanel.vue";
import TimelineSlider from "@/components/socialcircles/TimelineSlider.vue";
import NodeFloatingCard from "@/components/socialcircles/NodeFloatingCard.vue";
import EdgeSidebar from "@/components/socialcircles/EdgeSidebar.vue";
import ZoomControls from "@/components/socialcircles/ZoomControls.vue";
import LoadingState from "@/components/socialcircles/LoadingState.vue";
import EmptyState from "@/components/socialcircles/EmptyState.vue";
import ErrorState from "@/components/socialcircles/ErrorState.vue";
import ActiveFilterPills from "@/components/socialcircles/ActiveFilterPills.vue";
import NetworkLegend from "@/components/socialcircles/NetworkLegend.vue";
import ExportMenu from "@/components/socialcircles/ExportMenu.vue";
import ConnectionTooltip from "@/components/socialcircles/ConnectionTooltip.vue";
import KeyboardShortcutsModal from "@/components/socialcircles/KeyboardShortcutsModal.vue";
import SearchInput, { MAX_RESULTS } from "@/components/socialcircles/SearchInput.vue";
import StatsPanel from "@/components/socialcircles/StatsPanel.vue";
import PathFinderPanel from "@/components/socialcircles/PathFinderPanel.vue";
import BottomSheet from "@/components/socialcircles/BottomSheet.vue";
import MobileFilterFab from "@/components/socialcircles/MobileFilterFab.vue";

// Initialize the main orchestrator composable
const socialCircles = useSocialCircles();

// Initialize analytics tracking
const analytics = useAnalytics();

// Mobile detection and filter panel state
const { isMobile, isFiltersOpen, toggleFilters, closeFilters } = useMobile();

// Typed refs for composables (avoids inline import casts)
const typedNodes = computed(() => socialCircles.nodes.value as ApiNode[]);
const typedEdges = computed(() => socialCircles.edges.value as ApiEdge[]);

// Initialize path finder composable
const pathFinder = usePathFinder(typedNodes, typedEdges);

// Initialize find similar composable
const findSimilar = useFindSimilar(typedNodes, typedEdges);

// Destructure commonly used values
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
  // Toggle selection (new panel behavior)
  toggleSelectNode,
  toggleSelectEdge,
  closePanel,
  isPanelOpen,
  isNodeSelected,
  isEdgeSelected,

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
} = socialCircles;

// Note: useRouter() will be needed when entity-detail route is implemented

// Viewport tracking for smart card positioning
const { width: viewportWidth, height: viewportHeight } = useWindowSize();
const viewport = computed(() => ({
  width: viewportWidth.value,
  height: viewportHeight.value,
}));

// NetworkGraph ref for zoom controls and export
const networkGraphRef = ref<InstanceType<typeof NetworkGraph> | null>(null);

// Get node position from Cytoscape for floating card positioning
function getNodePosition(nodeId: NodeId): Position | null {
  const cy = networkGraphRef.value?.getCytoscape();
  if (!cy) return null;
  const node = cy.$id(nodeId);
  if (node.length === 0) return null;
  const renderedPos = node.renderedPosition();
  return { x: renderedPos.x, y: renderedPos.y };
}

// Computed card position based on selected node
const cardPosition = computed((): Position | null => {
  if (!selectedNode.value) return null;
  return getNodePosition(selectedNode.value.id);
});

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

// Keyboard shortcuts modal state
const showKeyboardShortcuts = ref(false);

// Search state
const searchQuery = ref("");
// Tracks the latest typed text before a search selection. Due to SearchInput's
// 300ms debounce, the dropdown may show results for an older query if the user
// types fast and clicks a result before the debounce fires. In that case this
// ref holds the most recent typed text, which is arguably the user's intent.
const preSelectSearchQuery = ref("");

// Stats panel collapsed state
const statsCollapsed = ref(false);

// Handle search query updates from typing (not from selection)
function handleSearchQueryUpdate(value: string) {
  searchQuery.value = value;
  preSelectSearchQuery.value = value;
}

// Handle search result selection - center graph on selected node
function handleSearchSelect(node: { id: string }) {
  // Capture the pre-selection search query before selectNode triggers a v-model update
  const query = preSelectSearchQuery.value.trim().toLowerCase();
  // Cap at MAX_RESULTS to match the SearchInput dropdown limit.
  // The user only ever sees up to MAX_RESULTS results, so analytics should reflect that.
  const totalMatches = query
    ? nodes.value.filter((n) => n.name.toLowerCase().includes(query)).length
    : 0;
  const resultCount = Math.min(totalMatches, MAX_RESULTS);

  // Track search before the early return so every search selection is recorded,
  // even when the node is not in the current filtered view.
  analytics.trackSearch(preSelectSearchQuery.value, resultCount);

  // Verify node exists in current filtered set before selecting
  const nodeExists = filteredNodes.value.some((n) => n.id === node.id);
  if (!nodeExists) {
    showToastMessage("Node not in current view");
    return;
  }

  selectNode(node.id);
  const cy = networkGraphRef.value?.getCytoscape();
  if (cy) {
    const cyNode = cy.getElementById(node.id);
    if (cyNode.length) {
      cy.animate({
        center: { eles: cyNode },
        zoom: cy.zoom(),
        duration: 300,
      });
    }
  }
}

// Handle find path between two nodes (W2-5)
function handleFindPath(start: string, end: string) {
  pathFinder.setStart(start as NodeId);
  pathFinder.setEnd(end as NodeId);
  pathFinder.findPath();
}

// Handle find similar action from context menu (W2-6)
function handleFindSimilar(nodeId: NodeId) {
  findSimilar.findSimilar(nodeId, 3);
  const results = findSimilar.similarNodes.value;
  if (results.length > 0) {
    const names = results.map((n: SimilarNode) => n.node.name).join(", ");
    showToastMessage(`Similar: ${names}`);
  } else {
    showToastMessage("No similar nodes found");
  }
}

// Wire up keyboard shortcuts
useNetworkKeyboard({
  onZoomIn: () => networkGraphRef.value?.zoomIn(),
  onZoomOut: () => networkGraphRef.value?.zoomOut(),
  onFit: () => networkGraphRef.value?.fitToView(),
  onTogglePlay: togglePlayback,
  onEscape: () => {
    if (showKeyboardShortcuts.value) {
      showKeyboardShortcuts.value = false;
    } else {
      closePanel();
    }
  },
  onHelp: () => {
    showKeyboardShortcuts.value = true;
  },
  onCycleLayout: () => networkGraphRef.value?.cycleMode(),
});

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
    // O(1) lookup via precomputed map
    const edge = edgeMap.value.get(edgeId);
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

// Get node name by ID for tooltip display - O(1) via precomputed map
function getNodeName(nodeId: string): string {
  const node = nodeMap.value.get(nodeId);
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
    analytics.trackExport("png");
  } else {
    showToastMessage(result.error || "Export failed");
  }
}

function handleExportJson() {
  try {
    exportJson();
    showToastMessage("JSON exported successfully");
    analytics.trackExport("json");
  } catch {
    showToastMessage("JSON export failed");
  }
}

async function handleShare() {
  const result = await shareUrl();
  if (result.success) {
    if (result.method === "clipboard") {
      showToastMessage("Link copied to clipboard");
    }
    // Native share doesn't need a toast - the OS handles it
    analytics.trackExport("url");
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

// Lookup maps for O(1) access in hover/select handlers
const edgeMap = computed(() => {
  const map = new Map<string, (typeof edges.value)[0]>();
  for (const edge of edges.value) {
    map.set(edge.id, edge);
  }
  return map;
});

const nodeMap = computed(() => {
  const map = new Map<string, (typeof nodes.value)[0]>();
  for (const node of nodes.value) {
    map.set(node.id, node);
  }
  return map;
});

// Computed states
const showGraph = computed(
  () => !isLoading.value && !hasError.value && filteredNodes.value.length > 0
);
const showEmpty = computed(
  () => !isLoading.value && !hasError.value && filteredNodes.value.length === 0
);

// Panel visibility for hiding controls (uses isPanelOpen from composable)
const showDetailPanel = computed(() => isPanelOpen.value);

// Type-cast computed properties for panel components (avoids readonly/mutable type conflicts)
const selectedNodeForCard = computed((): ApiNode | null => {
  return selectedNode.value as ApiNode | null;
});

const selectedEdgeForSidebar = computed((): ApiEdge | null => {
  return selectedEdge.value as ApiEdge | null;
});

const nodesForPanel = computed((): ApiNode[] => {
  return filteredNodes.value as ApiNode[];
});

const edgesForPanel = computed((): ApiEdge[] => {
  return filteredEdges.value as ApiEdge[];
});

// Type-cast nodes for SearchInput (avoids readonly/mutable type conflicts)
const nodesForSearch = computed((): ApiNode[] => {
  return nodes.value as ApiNode[];
});

// Type-cast meta for StatsPanel (avoids null type conflict)
// Uses DEFAULT_TIMELINE_STATE for consistent year defaults
const metaForStats = computed((): SocialCirclesMeta => {
  return (meta.value ?? {
    total_books: 0,
    total_authors: 0,
    total_publishers: 0,
    total_binders: 0,
    date_range: [DEFAULT_TIMELINE_STATE.minYear, DEFAULT_TIMELINE_STATE.maxYear] as [
      number,
      number,
    ],
    generated_at: new Date().toISOString(),
    truncated: false,
  }) as SocialCirclesMeta;
});

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

// Handle node selection from graph (with toggle behavior)
function handleNodeSelect(nodeId: string | null) {
  if (nodeId) {
    toggleSelectNode(nodeId);
    // Only track if the panel was opened (not toggled closed)
    if (isPanelOpen.value) {
      const node = nodeMap.value.get(nodeId);
      if (node) analytics.trackNodeSelect(node as ApiNode);
    }
  } else {
    clearSelection();
  }
}

// Handle edge selection from graph (with toggle behavior)
function handleEdgeSelect(edgeId: string | null) {
  if (edgeId) {
    toggleSelectEdge(edgeId);
    // Only track if the panel was opened (not toggled closed)
    if (isPanelOpen.value) {
      const edge = edgeMap.value.get(edgeId);
      if (edge) analytics.trackEdgeSelect(edge as ApiEdge);
    }
  } else {
    clearSelection();
  }
}

// Handle edge selection from floating card
function handleSelectEdge(edgeId: EdgeId) {
  selectEdge(edgeId as string);
}

// Handle view profile navigation
// Note: entity-detail route doesn't exist yet - feature planned for future
function handleViewProfile(_nodeId: NodeId) {
  // TODO: Navigate to entity detail page when route exists
  // void router.push({ name: "entity-detail", params: { id: nodeId } });
  showToastMessage("Entity profiles coming soon");
}

// Handle viewport changes (pan/zoom) - close floating card since position becomes stale
function handleViewportChange() {
  if (isPanelOpen.value) {
    closePanel();
  }
}

// Handle filter changes - delegates to orchestrator and tracks analytics
function handleFilterChange(key: keyof FilterState, value: unknown) {
  applyFilter(key, value);
  analytics.trackFilterChange(key, value);
}

// Handle filter reset - clears all filters and tracks the reset event
function handleFilterReset() {
  resetFilters();
  analytics.trackFilterReset();
}

// Handle individual filter removal - removes filter and tracks analytics
function handleFilterRemove(key: string) {
  // Capture the previous value before removal for analytics context
  const previousValue = filterState.value[key as keyof FilterState] ?? null;
  removeFilter(key);
  analytics.trackFilterRemove(key, previousValue);
}

// Handle mobile filter reset - resets filters with analytics tracking AND closes the bottom sheet
function handleMobileFilterReset() {
  handleFilterReset();
  closeFilters();
}

// Handle layout mode changes from NetworkGraph
function handleLayoutChange(mode: LayoutMode) {
  analytics.trackLayoutChange(mode);
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
      <div class="header-center">
        <SearchInput
          :model-value="searchQuery"
          :nodes="nodesForSearch"
          @update:model-value="handleSearchQueryUpdate"
          @select="handleSearchSelect"
        />
      </div>
      <div class="header-right">
        <ExportMenu
          @export-png="handleExportPng"
          @export-json="handleExportJson"
          @share="handleShare"
        />
      </div>
    </header>

    <!-- Truncation Warning -->
    <div v-if="meta?.truncated" class="truncation-warning">
      <span class="truncation-warning__icon">⚠</span>
      <span>Data limited to {{ meta.total_books }} books. Some connections may not be shown.</span>
    </div>

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
    <EmptyState v-else-if="showEmpty" @reset-filters="handleFilterReset" />

    <!-- Main Content (Desktop) -->
    <div v-else-if="showGraph && !isMobile" class="social-circles-content">
      <!-- Filter Panel (left sidebar) -->
      <aside class="filter-sidebar">
        <FilterPanel
          :filter-state="filterState"
          :nodes="nodesForSearch"
          @update:filter="handleFilterChange"
          @reset="handleFilterReset"
        />

        <!-- Active Filter Pills -->
        <ActiveFilterPills
          v-if="filterPills.length > 0"
          :filters="filterPills"
          @remove="handleFilterRemove"
          @clear-all="handleFilterReset"
        />

        <!-- Statistics Panel -->
        <StatsPanel
          :nodes="nodesForPanel"
          :edges="edgesForPanel"
          :meta="metaForStats"
          :is-collapsed="statsCollapsed"
          @toggle="statsCollapsed = !statsCollapsed"
        />

        <!-- Path Finder Panel (W2-5) -->
        <PathFinderPanel
          :nodes="nodesForPanel"
          :path="pathFinder.path.value"
          :is-calculating="pathFinder.isCalculating.value"
          @find-path="handleFindPath"
          @clear="pathFinder.clear"
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
            @viewport-change="handleViewportChange"
            @layout-change="handleLayoutChange"
          />

          <!-- Zoom Controls (top-right of graph) - hide when detail panel open -->
          <div v-show="!showDetailPanel" class="zoom-controls-container">
            <ZoomControls
              @zoom-in="handleZoomIn"
              @zoom-out="handleZoomOut"
              @fit="handleFitToView"
            />
          </div>

          <!-- Legend (bottom-right of graph) - hide when detail panel open -->
          <div v-show="!showDetailPanel" class="legend-container">
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

      <!-- Node Floating Card (smart positioned near clicked node) -->
      <NodeFloatingCard
        v-if="isNodeSelected && isPanelOpen"
        :node="selectedNodeForCard"
        :node-position="cardPosition"
        :viewport-size="viewport"
        :edges="edgesForPanel"
        :nodes="nodesForPanel"
        :is-open="isPanelOpen"
        @close="closePanel"
        @select-edge="handleSelectEdge"
        @view-profile="handleViewProfile"
        @find-similar="handleFindSimilar"
      />

      <!-- Edge Sidebar (slides in from right when edge selected) -->
      <EdgeSidebar
        v-if="isEdgeSelected && isPanelOpen"
        :edge="selectedEdgeForSidebar"
        :nodes="nodesForPanel"
        :is-open="isPanelOpen"
        @close="closePanel"
        @select-node="(nodeId: NodeId) => selectNode(nodeId as string)"
      />

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

    <!-- Main Content (Mobile) -->
    <div v-else-if="showGraph && isMobile" class="social-circles-content mobile-layout">
      <!-- Graph Area (full width on mobile) -->
      <main class="graph-area mobile-graph-area">
        <!-- Active Filter Pills (above graph on mobile) -->
        <div v-if="filterPills.length > 0" class="mobile-filter-pills">
          <ActiveFilterPills
            :filters="filterPills"
            @remove="handleFilterRemove"
            @clear-all="handleFilterReset"
          />
        </div>

        <!-- Graph viewport -->
        <div class="graph-viewport mobile-graph-viewport">
          <NetworkGraph
            ref="networkGraphRef"
            :elements="cytoscapeElements"
            :selected-node="selectedNode"
            :selected-edge="selectedEdge"
            :highlighted-nodes="highlightedNodes"
            :highlighted-edges="highlightedEdges"
            class="mobile-network-graph"
            @node-select="handleNodeSelect"
            @edge-select="handleEdgeSelect"
            @edge-hover="handleEdgeHover"
            @viewport-change="handleViewportChange"
            @layout-change="handleLayoutChange"
          />

          <!-- Zoom Controls -->
          <div v-show="!showDetailPanel && !isFiltersOpen" class="zoom-controls-container">
            <ZoomControls
              @zoom-in="handleZoomIn"
              @zoom-out="handleZoomOut"
              @fit="handleFitToView"
            />
          </div>

          <!-- Legend -->
          <div v-show="!showDetailPanel && !isFiltersOpen" class="legend-container mobile-legend">
            <NetworkLegend />
          </div>
        </div>

        <!-- Timeline -->
        <div class="timeline-area mobile-timeline">
          <TimelineSlider
            :min-year="timelineState.minYear"
            :max-year="timelineState.maxYear"
            :current-year="timelineState.currentYear"
            :mode="timelineState.mode"
            :is-playing="timelineState.isPlaying"
            @year-change="setYear"
            @play="togglePlayback"
            @pause="togglePlayback"
          />
        </div>
      </main>

      <!-- Mobile Filter FAB -->
      <MobileFilterFab :active-filter-count="filterPills.length" @click="toggleFilters" />

      <!-- Mobile Filter BottomSheet -->
      <BottomSheet v-model="isFiltersOpen" title="Filters">
        <FilterPanel
          :filter-state="filterState"
          :nodes="nodesForSearch"
          class="mobile-filter-panel"
          @update:filter="handleFilterChange"
          @reset="handleMobileFilterReset"
        />
      </BottomSheet>
    </div>

    <!-- Keyboard Shortcuts Modal -->
    <KeyboardShortcutsModal
      :is-open="showKeyboardShortcuts"
      @close="showKeyboardShortcuts = false"
    />

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

.truncation-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.5rem;
  background-color: var(--color-victorian-gold-light, #f5e6c8);
  border-bottom: 1px solid var(--color-victorian-gold-muted, #d4af37);
  color: var(--color-victorian-ink-dark, #2d2d2a);
  font-size: 0.875rem;
  flex-shrink: 0;
}

.truncation-warning__icon {
  font-size: 1rem;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.header-center {
  flex: 1;
  max-width: 320px;
  margin: 0 1rem;
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

/* Responsive adjustments */
@media (max-width: 1024px) {
  .filter-sidebar {
    width: 240px;
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

/* Mobile-specific styles */
.mobile-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.mobile-graph-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.mobile-filter-pills {
  padding: 0.5rem;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
}

.mobile-graph-viewport {
  flex: 1;
  position: relative;
  min-height: 0;
}

.mobile-network-graph {
  width: 100%;
  height: 100%;
}

.mobile-legend {
  bottom: 1rem;
  left: 1rem;
  right: auto;
}

.mobile-timeline {
  padding: 0.75rem;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border-top: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0));
}

.mobile-filter-panel {
  max-height: none;
  overflow: visible;
}

/* Hide filter sidebar on mobile */
@media (max-width: 767px) {
  .filter-sidebar {
    display: none;
  }
}
</style>
