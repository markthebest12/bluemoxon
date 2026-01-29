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
import { ref, shallowRef, onMounted, onUnmounted, watch } from "vue";
import { LAYOUT_CONFIGS } from "@/constants/socialCircles";

// Props
interface Props {
  elements?: ElementDefinition[];
  selectedNode?: { id: string } | null;
  selectedEdge?: { id: string } | null;
  highlightedNodes?: string[];
  highlightedEdges?: string[];
}

const props = withDefaults(defineProps<Props>(), {
  elements: () => [],
  selectedNode: null,
  selectedEdge: null,
  highlightedNodes: () => [],
  highlightedEdges: () => [],
});

// Emits
const emit = defineEmits<{
  "node-select": [nodeId: string | null];
  "edge-select": [edgeId: string | null];
  "node-hover": [nodeId: string | null];
  "edge-hover": [edgeId: string | null, event: MouseEvent | null];
  "viewport-change": [];
}>();

// Refs
const containerRef = ref<HTMLDivElement | null>(null);
const cy = shallowRef<Core | null>(null);
const isInitialized = ref(false);

// Victorian stylesheet
// Note: Cytoscape's types don't properly support "data(...)" dynamic values,
// so we cast the stylesheet to the expected type
function getCytoscapeStylesheet(): StylesheetStyle[] {
  return [
    {
      selector: "node",
      style: {
        "background-color": "data(nodeColor)",
        shape: "data(nodeShape)",
        width: "data(nodeSize)",
        height: "data(nodeSize)",
        label: "data(name)",
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

// Track element IDs to avoid unnecessary re-layouts
let lastElementIds: Set<string> = new Set();

// Watch elements for filter changes - only re-layout if elements actually changed
watch(
  () => props.elements,
  (newElements) => {
    if (!cy.value) return;

    // Check if element IDs changed (not just object references)
    const newIds = new Set(newElements.map((e) => e.data?.id).filter(Boolean) as string[]);
    const idsChanged =
      newIds.size !== lastElementIds.size || [...newIds].some((id) => !lastElementIds.has(id));

    if (!idsChanged) return; // Skip if same elements

    lastElementIds = newIds;

    cy.value.batch(() => {
      cy.value!.elements().remove();
      cy.value!.add(newElements);
    });
    cy.value.layout(LAYOUT_CONFIGS.force as LayoutOptions).run();
  },
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
});
</script>

<template>
  <div ref="containerRef" class="network-graph" />
</template>

<style scoped>
.network-graph {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background-color: var(--color-victorian-paper-cream, #f8f5f0);
}
</style>
