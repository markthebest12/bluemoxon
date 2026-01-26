# NetworkGraph Cytoscape Wiring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire Cytoscape.js into NetworkGraph.vue to render the social circles graph with Victorian styling.

**Architecture:** NetworkGraph receives pre-transformed Cytoscape elements via props from the parent view. It initializes Cytoscape on mount, watches for element changes, handles user interactions (tap, hover), and emits events. The orchestrator composable already handles all business logic.

**Tech Stack:** Vue 3 (Composition API), Cytoscape.js 3.33.1, TypeScript

---

## Task 1: Initialize Cytoscape on Mount

**Files:**
- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue`

**Step 1: Add Cytoscape import and instance ref**

```typescript
import cytoscape, { type Core, type EventObject, type ElementDefinition } from "cytoscape";
import { ref, onMounted, onUnmounted, watch, inject } from "vue";
import { LAYOUT_CONFIGS } from "@/constants/socialCircles";

// Cytoscape instance
const cy = ref<Core | null>(null);
```

**Step 2: Update props interface**

```typescript
interface Props {
  elements: ElementDefinition[];
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
```

**Step 3: Initialize Cytoscape in onMounted**

```typescript
onMounted(() => {
  if (!containerRef.value) return;

  cy.value = cytoscape({
    container: containerRef.value,
    elements: props.elements,
    style: getCytoscapeStylesheet(),
    layout: LAYOUT_CONFIGS.force,
    minZoom: 0.3,
    maxZoom: 3,
    wheelSensitivity: 0.3,
  });

  // Set up event handlers
  setupEventHandlers();
  isInitialized.value = true;
});
```

**Step 4: Clean up on unmount**

```typescript
onUnmounted(() => {
  if (cy.value) {
    cy.value.destroy();
    cy.value = null;
  }
});
```

**Step 5: Verify in browser**

Run: `npm run --prefix frontend dev`
Navigate to: http://localhost:5173/socialcircles
Expected: Graph renders with nodes and edges visible

**Step 6: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "feat(socialcircles): Initialize Cytoscape in NetworkGraph"
```

---

## Task 2: Add Victorian Stylesheet

**Files:**
- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue`

**Step 1: Create stylesheet function**

```typescript
function getCytoscapeStylesheet(): cytoscape.Stylesheet[] {
  return [
    // Base node style
    {
      selector: "node",
      style: {
        "background-color": "data(style.background-color)",
        shape: "data(style.shape)",
        width: "data(style.width)",
        height: "data(style.height)",
        label: "data(name)",
        "font-size": "10px",
        "font-family": "var(--font-serif, Georgia, serif)",
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
    // Base edge style
    {
      selector: "edge",
      style: {
        "line-color": "data(style.line-color)",
        "line-style": "data(style.line-style)",
        "line-opacity": "data(style.line-opacity)",
        width: "data(style.width)",
        "curve-style": "bezier",
        "target-arrow-shape": "none",
        "transition-property": "line-color, width, line-opacity",
        "transition-duration": "150ms",
      },
    },
    // Hover state
    {
      selector: "node:hover",
      style: {
        "border-width": 2,
        "border-color": "#c9a227",
        "z-index": 10,
      },
    },
    // Selected state
    {
      selector: "node:selected",
      style: {
        "border-width": 3,
        "border-color": "#722f37",
        "background-opacity": 1,
        "z-index": 20,
      },
    },
    // Highlighted nodes (connected to selected)
    {
      selector: "node.highlighted",
      style: {
        "border-width": 2,
        "border-color": "#3a6b5c",
        "background-opacity": 1,
      },
    },
    // Dimmed nodes (not connected to selected)
    {
      selector: "node.dimmed",
      style: {
        "background-opacity": 0.3,
        "border-opacity": 0.3,
        "text-opacity": 0.3,
      },
    },
    // Highlighted edges
    {
      selector: "edge.highlighted",
      style: {
        "line-opacity": 1,
        width: 4,
        "z-index": 10,
      },
    },
    // Dimmed edges
    {
      selector: "edge.dimmed",
      style: {
        "line-opacity": 0.15,
      },
    },
  ];
}
```

**Step 2: Verify styling in browser**

Navigate to: http://localhost:5173/socialcircles
Expected: Nodes have different shapes/colors by type, edges have Victorian colors

**Step 3: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "feat(socialcircles): Add Victorian stylesheet for Cytoscape"
```

---

## Task 3: Handle User Interactions

**Files:**
- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue`

**Step 1: Update emits**

```typescript
const emit = defineEmits<{
  "node-select": [nodeId: string | null];
  "edge-select": [edgeId: string | null];
  "node-hover": [nodeId: string | null];
  "edge-hover": [edgeId: string | null];
}>();
```

**Step 2: Create event handler setup function**

```typescript
function setupEventHandlers() {
  if (!cy.value) return;

  // Node tap (click)
  cy.value.on("tap", "node", (event: EventObject) => {
    const nodeId = event.target.id();
    emit("node-select", nodeId);
  });

  // Edge tap
  cy.value.on("tap", "edge", (event: EventObject) => {
    const edgeId = event.target.id();
    emit("edge-select", edgeId);
  });

  // Background tap (deselect)
  cy.value.on("tap", (event: EventObject) => {
    if (event.target === cy.value) {
      emit("node-select", null);
      emit("edge-select", null);
    }
  });

  // Node hover
  cy.value.on("mouseover", "node", (event: EventObject) => {
    emit("node-hover", event.target.id());
  });

  cy.value.on("mouseout", "node", () => {
    emit("node-hover", null);
  });

  // Edge hover
  cy.value.on("mouseover", "edge", (event: EventObject) => {
    emit("edge-hover", event.target.id());
  });

  cy.value.on("mouseout", "edge", () => {
    emit("edge-hover", null);
  });
}
```

**Step 3: Verify interactions in browser**

Navigate to: http://localhost:5173/socialcircles
Expected:
- Click node → detail panel opens
- Click background → panel closes
- Hover node → cursor changes

**Step 4: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "feat(socialcircles): Add click and hover event handlers"
```

---

## Task 4: Watch for Element Changes

**Files:**
- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue`

**Step 1: Add watch for elements prop**

```typescript
watch(
  () => props.elements,
  (newElements) => {
    if (!cy.value) return;

    // Batch update for performance
    cy.value.batch(() => {
      // Remove all existing elements
      cy.value!.elements().remove();
      // Add new elements
      cy.value!.add(newElements);
    });

    // Re-run layout
    cy.value.layout(LAYOUT_CONFIGS.force).run();
  },
  { deep: true }
);
```

**Step 2: Verify filter changes update graph**

Navigate to: http://localhost:5173/socialcircles
Action: Uncheck "Publishers" in filter panel
Expected: Publisher nodes disappear, graph re-layouts

**Step 3: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "feat(socialcircles): Watch elements prop for filter changes"
```

---

## Task 5: Handle Selection and Highlighting

**Files:**
- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue`

**Step 1: Watch for selection changes**

```typescript
watch(
  () => props.selectedNode,
  (newNode) => {
    if (!cy.value) return;

    // Clear previous selection
    cy.value.nodes().unselect();

    if (newNode?.id) {
      const node = cy.value.getElementById(newNode.id);
      if (node.length) {
        node.select();
      }
    }
  }
);
```

**Step 2: Watch for highlight changes**

```typescript
watch(
  () => [props.highlightedNodes, props.highlightedEdges],
  ([nodeIds, edgeIds]) => {
    if (!cy.value) return;

    // Remove all highlight classes
    cy.value.elements().removeClass("highlighted dimmed");

    if (nodeIds && nodeIds.length > 0) {
      const highlightedNodeSet = new Set(nodeIds);
      const highlightedEdgeSet = new Set(edgeIds || []);

      // Add highlighted class to specified nodes/edges
      cy.value.nodes().forEach((node) => {
        if (highlightedNodeSet.has(node.id())) {
          node.addClass("highlighted");
        } else {
          node.addClass("dimmed");
        }
      });

      cy.value.edges().forEach((edge) => {
        if (highlightedEdgeSet.has(edge.id())) {
          edge.addClass("highlighted");
        } else {
          edge.addClass("dimmed");
        }
      });
    }
  },
  { deep: true }
);
```

**Step 3: Verify highlighting in browser**

Navigate to: http://localhost:5173/socialcircles
Action: Click a node
Expected: Selected node highlighted, connected nodes/edges highlighted, others dimmed

**Step 4: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "feat(socialcircles): Handle selection and neighbor highlighting"
```

---

## Task 6: Expose Cytoscape Instance for Zoom Controls

**Files:**
- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue`
- Modify: `frontend/src/views/SocialCirclesView.vue`

**Step 1: Update defineExpose in NetworkGraph**

```typescript
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
```

**Step 2: Update SocialCirclesView to use ref**

In SocialCirclesView.vue, add:
```typescript
import { ref } from "vue";

const networkGraphRef = ref<InstanceType<typeof NetworkGraph> | null>(null);

// Update zoom handlers to use ref
function handleZoomIn() {
  networkGraphRef.value?.zoomIn();
}

function handleZoomOut() {
  networkGraphRef.value?.zoomOut();
}

function handleFitToView() {
  networkGraphRef.value?.fitToView();
}
```

And in template:
```html
<NetworkGraph
  ref="networkGraphRef"
  ...
/>

<ZoomControls
  @zoom-in="handleZoomIn"
  @zoom-out="handleZoomOut"
  @fit="handleFitToView"
/>
```

**Step 3: Verify zoom controls work**

Navigate to: http://localhost:5173/socialcircles
Action: Click +, -, and fit buttons
Expected: Graph zooms in, out, and fits to view

**Step 4: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git add frontend/src/views/SocialCirclesView.vue
git commit -m "feat(socialcircles): Wire zoom controls to Cytoscape instance"
```

---

## Task 7: Final Integration Test

**Step 1: Run frontend lint**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 2: Run frontend type check**

Run: `npm run --prefix frontend type-check`
Expected: No errors

**Step 3: Manual verification checklist**

Navigate to: http://localhost:5173/socialcircles

- [ ] Graph renders with 220 nodes visible
- [ ] Authors are ellipses (green shades)
- [ ] Publishers are rectangles (gold shades)
- [ ] Binders are diamonds (burgundy shades)
- [ ] Edges connect nodes with Victorian colors
- [ ] Click node → detail panel opens
- [ ] Click background → panel closes
- [ ] Uncheck "Publishers" → publishers disappear
- [ ] Zoom +/- buttons work
- [ ] Fit button centers graph
- [ ] Timeline slider filters by year

**Step 4: Create PR**

```bash
git add .
git commit -m "feat(socialcircles): Complete Cytoscape integration for NetworkGraph"
gh pr create --base staging --title "feat(socialcircles): Wire Cytoscape into NetworkGraph" --body "## Summary
- Initialize Cytoscape.js in NetworkGraph component
- Add Victorian-themed stylesheet (shapes, colors, animations)
- Handle tap/hover events with emit to parent
- Watch elements prop for filter updates
- Handle selection and neighbor highlighting
- Wire zoom controls to Cytoscape instance

## Test Plan
- [x] Frontend lint passes
- [x] Frontend type-check passes
- [x] Manual testing of all interactions

Closes #1317, #1320, #1321, #1337"
```

---

## Files Changed Summary

| File | Changes |
|------|---------|
| `frontend/src/components/socialcircles/NetworkGraph.vue` | Complete rewrite - Cytoscape integration |
| `frontend/src/views/SocialCirclesView.vue` | Add ref for NetworkGraph, wire zoom handlers |

## Issues Closed

- #1317 - Click node to highlight connections
- #1320 - Node shapes and colors by type
- #1321 - Node size proportional to collection count
- #1337 - Zoom controls overlay
