/**
 * useSocialCircles - Main orchestrator composable.
 * Combines all social circles composables into a single interface.
 */

import { computed, watch, shallowRef, type Ref } from "vue";
import { useNetworkData } from "./useNetworkData";
import { useNetworkFilters } from "./useNetworkFilters";
import { useNetworkSelection } from "./useNetworkSelection";
import { useNetworkTimeline } from "./useNetworkTimeline";
import { useUrlState } from "./useUrlState";
import { useHubMode } from "./useHubMode";
import { transformToCytoscapeElements } from "@/utils/socialCircles/dataTransformers";
import type {
  ApiNode,
  ApiEdge,
  ConnectionType,
  EdgeId,
  Era,
  NodeId,
  FilterState,
} from "@/types/socialCircles";
import type { Core as CytoscapeCore } from "cytoscape";

export function useSocialCircles() {
  // Cytoscape instance ref (set by NetworkGraph component)
  const cytoscapeInstance = shallowRef<CytoscapeCore | null>(null);

  // Compose all sub-composables
  const networkData = useNetworkData();
  const filters = useNetworkFilters();
  const selection = useNetworkSelection();
  const timeline = useNetworkTimeline();
  const urlState = useUrlState();

  // Computed: is loading
  const isLoading = computed(() => networkData.loadingState.value === "loading");
  const hasError = computed(() => networkData.loadingState.value === "error");

  // Computed: nodes from data
  const nodes = computed(() => networkData.data.value?.nodes ?? []);
  const edges = computed(() => networkData.data.value?.edges ?? []);
  const meta = computed(() => networkData.data.value?.meta ?? null);

  // Hub mode for progressive disclosure
  const hubMode = useHubMode(
    nodes as unknown as Ref<ApiNode[]>,
    edges as unknown as Ref<ApiEdge[]>
  );

  // Stage 1: Apply user filters (type, era, search, timeline)
  const filterPassedNodes = computed(() => {
    const nodeList = nodes.value;
    if (!nodeList.length) return [];

    return nodeList.filter((node) => {
      const f = filters.filters.value;

      // Node type filter
      if (node.type === "author" && !f.showAuthors) return false;
      if (node.type === "publisher" && !f.showPublishers) return false;
      if (node.type === "binder" && !f.showBinders) return false;

      // Tier filter (API returns TIER_1, TIER_2, TIER_3)
      if (f.tier1Only && node.tier !== "TIER_1") return false;

      // Era filter
      if (f.eras.length > 0 && node.era && !f.eras.includes(node.era)) {
        return false;
      }

      // Search filter
      if (f.searchQuery) {
        const query = f.searchQuery.toLowerCase();
        if (!node.name.toLowerCase().includes(query)) return false;
      }

      // Timeline filter (point mode)
      if (timeline.timeline.value.mode === "point") {
        const year = timeline.timeline.value.currentYear;
        if (node.type === "author") {
          const birth = node.birth_year || 0;
          const death = node.death_year || 9999;
          if (year < birth || year > death) return false;
        }
      }

      return true;
    });
  });

  // Stage 2: Apply hub mode on top of filter results
  const filteredNodes = computed(() => {
    const filtered = filterPassedNodes.value;
    if (hubMode.isFullyExpanded.value) return filtered;
    const visibleIds = hubMode.visibleNodeIds.value;
    return filtered.filter((n) => visibleIds.has(n.id));
  });

  // Computed: filtered edges (edges where both source and target are in filteredNodes)
  const filteredNodeIds = computed(() => new Set(filteredNodes.value.map((n) => n.id)));

  const filteredEdges = computed(() => {
    const edgeList = edges.value;
    const nodeIds = filteredNodeIds.value;
    if (!edgeList.length) return [];

    return edgeList.filter((edge) => {
      // Both endpoints must be visible
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
        return false;
      }

      // Connection type filter
      const f = filters.filters.value;
      if (f.connectionTypes.length > 0 && !f.connectionTypes.includes(edge.type)) {
        return false;
      }

      return true;
    });
  });

  // Computed: filter state for template binding
  const filterState = computed(() => filters.filters.value);

  // Computed: active filters as array for pills display
  const activeFilters = computed(() => {
    const result: Array<{ key: string; label: string; value: unknown }> = [];
    const f = filters.filters.value;

    if (!f.showAuthors) result.push({ key: "showAuthors", label: "Hide Authors", value: false });
    if (!f.showPublishers)
      result.push({ key: "showPublishers", label: "Hide Publishers", value: false });
    if (!f.showBinders) result.push({ key: "showBinders", label: "Hide Binders", value: false });
    if (f.tier1Only) result.push({ key: "tier1Only", label: "Tier 1 Only", value: true });
    if (f.searchQuery)
      result.push({
        key: "searchQuery",
        label: `Search: "${f.searchQuery}"`,
        value: f.searchQuery,
      });
    f.eras.forEach((era) => result.push({ key: `era:${era}`, label: `Era: ${era}`, value: era }));
    f.connectionTypes.forEach((ct) =>
      result.push({ key: `ct:${ct}`, label: `Connection: ${ct}`, value: ct })
    );

    return result;
  });

  // Selection state
  const selectedNode = computed(() => {
    const nodeId = selection.selection.value.selectedNodeId;
    if (!nodeId) return null;
    return nodes.value.find((n) => n.id === nodeId) ?? null;
  });

  // Edge selection - find edge by ID from selection state
  const selectedEdge = computed(() => {
    const edgeId = selection.selection.value.selectedEdgeId;
    if (!edgeId) return null;
    return edges.value.find((e) => e.id === edgeId) ?? null;
  });

  // Use computed properties from selection composable for proper reactivity
  const highlightedNodes = computed(() => selection.highlightedNodeIds.value);
  const highlightedEdges = computed(() => selection.highlightedEdgeIds.value);

  // Timeline state for template binding
  const timelineState = computed(() => timeline.timeline.value);

  // Apply a filter update (generic)
  function applyFilter(key: keyof FilterState, value: unknown) {
    switch (key) {
      case "showAuthors":
        filters.setShowAuthors(value as boolean);
        break;
      case "showPublishers":
        filters.setShowPublishers(value as boolean);
        break;
      case "showBinders":
        filters.setShowBinders(value as boolean);
        break;
      case "tier1Only":
        filters.setTier1Only(value as boolean);
        break;
      case "searchQuery":
        filters.setSearchQuery(value as string);
        break;
      case "connectionTypes":
        filters.setConnectionTypes(value as ConnectionType[]);
        break;
      case "eras":
        filters.setEras(value as Era[]);
        break;
    }
  }

  // Remove a specific filter
  function removeFilter(filterKey: string) {
    if (filterKey === "showAuthors") filters.setShowAuthors(true);
    else if (filterKey === "showPublishers") filters.setShowPublishers(true);
    else if (filterKey === "showBinders") filters.setShowBinders(true);
    else if (filterKey === "tier1Only") filters.setTier1Only(false);
    else if (filterKey === "searchQuery") filters.setSearchQuery("");
    else if (filterKey.startsWith("era:")) {
      const era = filterKey.substring(4) as Era;
      filters.toggleEra(era);
    } else if (filterKey.startsWith("ct:")) {
      const ct = filterKey.substring(3) as ConnectionType;
      filters.toggleConnectionType(ct);
    }
  }

  // Selection handlers
  function selectNode(nodeId: string) {
    selection.selectNode(nodeId as NodeId);
  }

  function selectEdge(edgeId: string) {
    selection.selectEdge(edgeId as EdgeId);
  }

  function clearSelection() {
    selection.clearSelection();
  }

  // Timeline handlers
  function setYear(year: number) {
    timeline.setCurrentYear(year);
  }

  function setRange(start: number, end: number) {
    timeline.setRange(start, end);
  }

  function togglePlayback() {
    timeline.togglePlayback();
  }

  function setPlaybackSpeed(speed: 0.5 | 1 | 2 | 5) {
    timeline.setPlaybackSpeed(speed);
  }

  // Graph operations
  function zoomIn() {
    if (cytoscapeInstance.value) {
      cytoscapeInstance.value.zoom(cytoscapeInstance.value.zoom() * 1.2);
    }
  }

  function zoomOut() {
    if (cytoscapeInstance.value) {
      cytoscapeInstance.value.zoom(cytoscapeInstance.value.zoom() / 1.2);
    }
  }

  function fitToView() {
    if (cytoscapeInstance.value) {
      cytoscapeInstance.value.fit(undefined, 50);
    }
  }

  // Get Cytoscape elements for rendering
  function getCytoscapeElements() {
    const m = meta.value;
    const elements = transformToCytoscapeElements({
      nodes: [...filteredNodes.value] as ApiNode[],
      edges: [...filteredEdges.value] as ApiEdge[],
      meta: {
        total_books: m?.total_books ?? 0,
        total_authors: m?.total_authors ?? 0,
        total_publishers: m?.total_publishers ?? 0,
        total_binders: m?.total_binders ?? 0,
        date_range: m?.date_range ? ([...m.date_range] as [number, number]) : [1800, 1900],
        generated_at: m?.generated_at ?? new Date().toISOString(),
        truncated: m?.truncated ?? false,
      },
    });

    // Inject hub mode badge data into node elements (#1655)
    for (const el of elements) {
      if (el.group === "nodes" && el.data?.id) {
        const hidden = hubMode.isFullyExpanded.value
          ? 0
          : hubMode.hiddenNeighborCount(el.data.id as NodeId);
        el.data.hiddenCount = hidden;
        el.data.label = hidden > 0 ? `${el.data.name}  +${hidden}` : el.data.name;
      }
    }

    return elements;
  }

  // Export functions
  async function exportPng(): Promise<{ success: boolean; error?: string }> {
    if (!cytoscapeInstance.value) {
      return { success: false, error: "Graph not initialized" };
    }

    try {
      const png = cytoscapeInstance.value.png({
        output: "blob",
        bg: "#fdfcfa",
        scale: 2,
      });

      // Download
      const url = URL.createObjectURL(png);
      try {
        const a = document.createElement("a");
        a.href = url;
        a.download = `social-circles-${Date.now()}.png`;
        a.click();
      } finally {
        URL.revokeObjectURL(url);
      }
      return { success: true };
    } catch (e) {
      const message = e instanceof Error ? e.message : "Export failed";
      return { success: false, error: message };
    }
  }

  function exportJson(): void {
    const data = {
      nodes: filteredNodes.value,
      edges: filteredEdges.value,
      meta: meta.value,
      exportedAt: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `social-circles-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function shareUrl(): Promise<{
    success: boolean;
    method: "native" | "clipboard";
    error?: string;
  }> {
    const url = window.location.href;

    // Try native share API first (mobile)
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Victorian Social Circles",
          text: "Check out these literary connections!",
          url,
        });
        return { success: true, method: "native" };
      } catch (e) {
        // User cancelled or error - fall through to clipboard
        if ((e as Error).name === "AbortError") {
          return { success: false, method: "native", error: "Cancelled" };
        }
      }
    }

    // Clipboard fallback
    try {
      await navigator.clipboard.writeText(url);
      return { success: true, method: "clipboard" };
    } catch {
      return { success: false, method: "clipboard", error: "Failed to copy to clipboard" };
    }
  }

  // Initialize: fetch data and restore state from URL
  async function initialize() {
    // Restore state from URL (waits for router to be ready)
    const urlParams = await urlState.initialize();

    // Apply URL filters
    if (urlParams.filters.showAuthors !== undefined) {
      filters.setShowAuthors(urlParams.filters.showAuthors);
    }
    if (urlParams.filters.showPublishers !== undefined) {
      filters.setShowPublishers(urlParams.filters.showPublishers);
    }
    if (urlParams.filters.showBinders !== undefined) {
      filters.setShowBinders(urlParams.filters.showBinders);
    }
    if (urlParams.filters.tier1Only !== undefined) {
      filters.setTier1Only(urlParams.filters.tier1Only);
    }
    if (urlParams.filters.searchQuery !== undefined) {
      filters.setSearchQuery(urlParams.filters.searchQuery);
    }
    if (urlParams.filters.connectionTypes) {
      filters.setConnectionTypes(urlParams.filters.connectionTypes);
    }
    if (urlParams.filters.eras) {
      filters.setEras(urlParams.filters.eras);
    }

    // Fetch data
    await networkData.fetchData();

    // Initialize hub mode (progressive disclosure)
    hubMode.initializeHubs();

    // Set up selection data
    if (networkData.data.value) {
      selection.setNodesAndEdges(
        [...networkData.data.value.nodes] as ApiNode[],
        [...networkData.data.value.edges] as ApiEdge[]
      );

      // Set date range from data (must happen before setting year from URL)
      const [minYear, maxYear] = networkData.data.value.meta.date_range;
      timeline.setDateRange(minYear, maxYear);

      // Apply URL timeline (after date range is set)
      if (urlParams.year) {
        timeline.setCurrentYear(urlParams.year);
      }

      // Apply URL selection
      if (urlParams.selectedNode) {
        selection.selectNode(urlParams.selectedNode);
      }
    }
  }

  // Cleanup
  function cleanup() {
    timeline.pause();
    selection.clearSelection();
    cytoscapeInstance.value = null;
  }

  // Set Cytoscape instance (called by NetworkGraph)
  function setCytoscapeInstance(cy: CytoscapeCore) {
    cytoscapeInstance.value = cy;
  }

  // Sync state changes to URL (consolidated watcher for filters, selection, and timeline)
  // URL updates are skipped during playback to avoid history spam.
  //
  // NOTE: Race condition on pause - if user scrubs within the 100ms debounce window after
  // playback stops, the "paused" year update may be superseded by the scrubbed year.
  // This is acceptable because the user's scrub action expresses their intended new state.
  // The debounce exists to batch rapid changes (like scrubbing) into single URL updates.
  watch(
    () => ({
      filters: filters.filters.value,
      selectedNodeId: selection.selection.value.selectedNodeId,
      currentYear: timeline.timeline.value.currentYear,
      isPlaying: timeline.timeline.value.isPlaying,
    }),
    ({ filters: f, selectedNodeId, currentYear, isPlaying }) => {
      if (urlState.isInitialized.value) {
        urlState.updateUrl({
          filters: {
            showAuthors: f.showAuthors,
            showPublishers: f.showPublishers,
            showBinders: f.showBinders,
            connectionTypes: [...f.connectionTypes],
            tier1Only: f.tier1Only,
            eras: [...f.eras],
            searchQuery: f.searchQuery,
          },
          selectedNode: selectedNodeId,
          year: currentYear,
          isPlaying,
        });
      }
    },
    { deep: true }
  );

  // Toggle selection handlers (for new panel components)
  function toggleSelectNode(nodeId: string) {
    selection.toggleSelectNode(nodeId as NodeId);
  }

  function toggleSelectEdge(edgeId: string) {
    selection.toggleSelectEdge(edgeId as EdgeId);
  }

  function closePanel() {
    selection.closePanel();
  }

  return {
    // Data
    nodes,
    edges,
    filteredNodes,
    filteredEdges,
    meta,

    // State
    loadingState: networkData.loadingState,
    error: networkData.error,
    isLoading,
    hasError,

    // Filters
    filterState,
    activeFilters,
    applyFilter,
    resetFilters: filters.resetFilters,
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
    isPanelOpen: selection.isPanelOpen,
    isNodeSelected: selection.isNodeSelected,
    isEdgeSelected: selection.isEdgeSelected,

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
    setCytoscapeInstance,

    // Export
    exportPng,
    exportJson,
    shareUrl,

    // Hub mode
    hubMode: {
      statusText: hubMode.statusText,
      isFullyExpanded: hubMode.isFullyExpanded,
      expandNode: hubMode.expandNode,
      expandMore: hubMode.expandMore,
      showMore: hubMode.showMore,
      hiddenNeighborCount: hubMode.hiddenNeighborCount,
      isExpanded: hubMode.isExpanded,
      hubLevel: hubMode.hubLevel,
    },

    // Lifecycle
    initialize,
    cleanup,
    refreshData: () => networkData.fetchData({ forceRefresh: true }),
  };
}
