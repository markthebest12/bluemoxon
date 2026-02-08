<!-- frontend/src/components/socialcircles/NetworkGraph.vue -->
<script setup lang="ts">
/**
 * NetworkGraph - Cytoscape.js wrapper for the social circles visualization.
 */

// Types are imported statically (erased at compile time, no bundle impact)
import type {
  Core,
  EventObject,
  ElementDefinition,
  StylesheetStyle,
  LayoutOptions,
} from "cytoscape";
// Cytoscape library is dynamically imported in onMounted for code splitting
import { ref, shallowRef, computed, onMounted, onUnmounted, watch } from "vue";
import { useMediaQuery } from "@vueuse/core";
import { LAYOUT_CONFIGS } from "@/constants/socialCircles";
import { useLayoutMode } from "@/composables/socialcircles";
import LayoutSwitcher from "./LayoutSwitcher.vue";
import MiniMap from "@/components/socialcircles/MiniMap.vue";
import type { LayoutMode } from "@/types/socialCircles";

// Props
interface Props {
  elements?: ElementDefinition[];
  selectedNode?: { id: string } | null;
  selectedEdge?: { id: string } | null;
  highlightedNodes?: string[];
  highlightedEdges?: string[];
  preservePositions?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  elements: () => [],
  selectedNode: null,
  selectedEdge: null,
  highlightedNodes: () => [],
  highlightedEdges: () => [],
  preservePositions: false,
});

// Emits
const emit = defineEmits<{
  "node-select": [nodeId: string | null];
  "edge-select": [edgeId: string | null];
  "node-hover": [nodeId: string | null];
  "edge-hover": [edgeId: string | null, event: MouseEvent | null];
  "viewport-change": [];
  "layout-change": [mode: LayoutMode];
}>();

// Handle layout mode change
function handleLayoutChange(mode: LayoutMode) {
  setMode(mode);
  emit("layout-change", mode);
}

// Refs
const containerRef = ref<HTMLDivElement | null>(null);
const cy = shallowRef<Core | null>(null);
const isInitialized = ref(false);

// Touch device detection for mobile-optimized interactions
const isCoarsePointer = useMediaQuery("(pointer: coarse)");
const isMobileViewport = useMediaQuery("(max-width: 767px)");
const isTouchDevice = computed(() => isCoarsePointer.value || isMobileViewport.value);

// Layout mode management
const { currentMode, isAnimating, setMode, cycleMode } = useLayoutMode(cy);

// Victorian stylesheet
// Note: Cytoscape's types don't properly support "data(...)" dynamic values,
// so we cast the stylesheet to the expected type
//
// nodeSize is pre-calculated by calculateNodeSize() in constants/socialCircles.ts:
// - Uses sqrt(bookCount) scaling with diminishing returns (sqrt(1)=1, sqrt(4)=2, sqrt(64)=8)
// - Formula: base + sqrt(max(bookCount, 1)) * perBook, clamped to max via Math.min
// - Author: 20px base, 5px/√book, 60px max (reached at 64 books)
// - Publisher: 25px base, 4px/√book, 65px max (reached at 100 books)
// - Binder: 20px base, 5px/√book, 55px max (reached at 49 books)
// - Negative/zero bookCount clamped to 1 via Math.max before sqrt
function getCytoscapeStylesheet(): StylesheetStyle[] {
  return [
    {
      selector: "node",
      style: {
        "background-color": "data(nodeColor)",
        shape: "data(nodeShape)",
        width: "data(nodeSize)",
        height: "data(nodeSize)",
        label: "data(label)",
        "font-size": "10px",
        "font-family": "Georgia, serif",
        "text-valign": "bottom",
        "text-margin-y": 5,
        color: "#3a3a38",
        "text-outline-width": 2,
        "text-outline-color": "#fdfcfa",
        "border-width": 1,
        "border-color": "#e8e4d9",
        "transition-property": "background-color, border-color, width, height",
        "transition-duration": "150ms",
      },
    },
    {
      selector: "node[hiddenCount > 0]",
      style: {
        "font-size": "9px",
        "text-wrap": "wrap" as never,
        "text-max-width": "100px" as never,
      },
    },
    {
      selector: "edge",
      style: {
        "line-color": "data(edgeColor)",
        "line-style": "data(edgeStyle)",
        "line-opacity": "data(edgeOpacity)",
        width: "data(edgeWidth)",
        "curve-style": "bezier",
        "target-arrow-shape": "none",
        "transition-property": "line-color, width, line-opacity",
        "transition-duration": "150ms",
      },
    },
    {
      selector: "node:active",
      style: {
        "overlay-opacity": 0,
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-width": 3,
        "border-color": "#722f37",
        "z-index": 20,
      },
    },
    {
      selector: "node.highlighted",
      style: {
        "border-width": 2,
        "border-color": "#3a6b5c",
      },
    },
    {
      selector: "node.dimmed",
      style: {
        opacity: 0.3,
      },
    },
    {
      selector: "edge.highlighted",
      style: {
        "line-opacity": 1,
        width: 4,
        "z-index": 10,
      },
    },
    {
      selector: "edge.dimmed",
      style: {
        "line-opacity": 0.15,
      },
    },
  ] as StylesheetStyle[];
}

// Event handlers
function setupEventHandlers() {
  if (!cy.value) return;

  cy.value.on("tap", "node", (event: EventObject) => {
    emit("node-select", event.target.id());
  });

  cy.value.on("tap", "edge", (event: EventObject) => {
    emit("edge-select", event.target.id());
  });

  cy.value.on("tap", (event: EventObject) => {
    if (event.target === cy.value) {
      emit("node-select", null);
      emit("edge-select", null);
    }
  });

  cy.value.on("mouseover", "node", (event: EventObject) => {
    emit("node-hover", event.target.id());
  });

  cy.value.on("mouseout", "node", () => {
    emit("node-hover", null);
  });

  cy.value.on("mouseover", "edge", (event: EventObject) => {
    emit("edge-hover", event.target.id(), event.originalEvent as MouseEvent);
  });

  cy.value.on("mouseout", "edge", () => {
    emit("edge-hover", null, null);
  });

  // Emit viewport changes (pan/zoom) so parent can close floating cards
  cy.value.on("pan zoom", () => {
    emit("viewport-change");
  });
}

// Lifecycle - dynamic import for code splitting (~300KB loaded after shell renders)
onMounted(async () => {
  if (!containerRef.value) return;

  // Dynamic import creates a separate chunk, improving First Contentful Paint
  const cytoscape = (await import("cytoscape")).default;
  const dagre = (await import("cytoscape-dagre")).default;
  cytoscape.use(dagre);

  cy.value = cytoscape({
    container: containerRef.value,
    elements: props.elements,
    style: getCytoscapeStylesheet(),
    layout: LAYOUT_CONFIGS.force as LayoutOptions,
    minZoom: 0.3,
    maxZoom: 3,
    // Omit wheelSensitivity to use Cytoscape default (1) and avoid deprecation warning
  });

  setupEventHandlers();
  isInitialized.value = true;
});

onUnmounted(() => {
  if (cy.value) {
    cy.value.destroy();
    cy.value = null;
  }
});

// Track element IDs to avoid unnecessary re-layouts (using Set for O(n) lookup)
let lastElementIds = new Set<string>();

// Cache node positions before re-layout for "show less" restoration
let positionCache = new Map<string, { x: number; y: number }>();

// Watch elements for filter changes - only re-layout if elements actually changed
watch(
  () => props.elements,
  (newElements) => {
    if (!cy.value) return;

    // Use Set for O(n) comparison instead of O(n log n) sorting
    // Filter out falsy IDs to prevent undefined/null from collapsing into single "" entry
    const newIdSet = new Set<string>(
      newElements.map((e) => e.data?.id).filter((id): id is NonNullable<typeof id> => Boolean(id))
    );
    // Check if any new ID wasn't in the old set (more intuitive: "what appeared?")
    const idsChanged =
      newIdSet.size !== lastElementIds.size || [...newIdSet].some((id) => !lastElementIds.has(id));

    if (!idsChanged) return; // Skip if same elements

    // Cache current positions before removing elements
    if (cy.value.nodes().length > 0) {
      positionCache = new Map(cy.value.nodes().map((n) => [n.id(), { ...n.position() }]));
    }

    // Use preserved positions when parent signals hub-level decrease
    const usePreset = props.preservePositions && positionCache.size > 0;

    lastElementIds = newIdSet;

    cy.value.batch(() => {
      cy.value!.elements().remove();
      cy.value!.add(newElements);
    });

    if (usePreset) {
      // Restore cached positions for remaining nodes (deterministic reversal)
      cy.value
        .layout({
          name: "preset",
          positions: (node: { id: () => string }) => positionCache.get(node.id()),
          fit: true,
          padding: ((LAYOUT_CONFIGS.force as Record<string, unknown>).padding as number) ?? 80,
        } as LayoutOptions)
        .run();
    } else {
      cy.value.layout(LAYOUT_CONFIGS.force as LayoutOptions).run();
    }
  },
  // flush: "post" ensures DOM is ready; deep: true is defensive in case elements
  // are ever mutated in-place (currently they're replaced via computed)
  { deep: true, flush: "post" }
);

// Watch selection
watch(
  () => props.selectedNode,
  (newNode) => {
    if (!cy.value) return;
    cy.value.nodes().unselect();
    if (newNode?.id) {
      const node = cy.value.getElementById(newNode.id);
      if (node.length) node.select();
    }
  }
);

// Watch highlights - use toRef to properly track prop changes
watch(
  [() => props.highlightedNodes, () => props.highlightedEdges],
  ([nodeIds, edgeIds]) => {
    if (!cy.value) return;
    cy.value.elements().removeClass("highlighted dimmed");

    if (nodeIds && nodeIds.length > 0) {
      const nodeSet = new Set(nodeIds);
      const edgeSet = new Set(edgeIds || []);

      cy.value.nodes().forEach((node) => {
        node.addClass(nodeSet.has(node.id()) ? "highlighted" : "dimmed");
      });

      cy.value.edges().forEach((edge) => {
        edge.addClass(edgeSet.has(edge.id()) ? "highlighted" : "dimmed");
      });
    }
  },
  { deep: true }
);

// Use immediate:true to apply correct styles if cy initializes after touch mode is detected
watch(
  isTouchDevice,
  (_isTouch) => {
    if (!cy.value) return;
    // Update node sizes for touch targets (larger on touch devices)
    cy.value.style().update();
  },
  { immediate: true }
);

// Expose methods for parent
defineExpose({
  getCytoscape: () => cy.value,
  fitToView: () => cy.value?.fit(undefined, 50),
  zoomIn: () => {
    if (cy.value) cy.value.zoom(cy.value.zoom() * 1.2);
  },
  zoomOut: () => {
    if (cy.value) cy.value.zoom(cy.value.zoom() / 1.2);
  },
  getZoom: () => cy.value?.zoom() ?? 1,
  cycleMode,
});
</script>

<template>
  <div class="network-graph-container">
    <div ref="containerRef" class="network-graph" data-testid="network-graph" />
    <div class="network-graph__controls">
      <LayoutSwitcher
        :model-value="currentMode"
        :disabled="isAnimating"
        @update:model-value="handleLayoutChange"
      />
    </div>
    <MiniMap v-if="isInitialized" :cy="cy" class="mini-map-overlay" />
  </div>
</template>

<style scoped>
.network-graph-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.network-graph {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background-color: var(--color-victorian-paper-cream, #f8f5f0);
}

.network-graph__controls {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 10;
}

.mini-map-overlay {
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  z-index: 10;
}
</style>
