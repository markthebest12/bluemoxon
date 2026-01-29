<script setup lang="ts">
/**
 * MiniMap - Small overview map showing entire graph with viewport indicator.
 *
 * Displays a miniaturized version of the graph and shows a rectangle
 * indicating the current viewport position. Click to pan the main view.
 */

import type { Core } from "cytoscape";
import { ref, watch, onUnmounted, computed } from "vue";

interface Props {
  cy?: Core | null;
  width?: number;
  height?: number;
}

const props = withDefaults(defineProps<Props>(), {
  cy: null,
  width: 150,
  height: 100,
});

// Visibility toggle
const isVisible = ref(true);

// Canvas ref for drawing
const canvasRef = ref<HTMLCanvasElement | null>(null);

// Store graph bounds for coordinate transformations
const graphBounds = ref({ x1: 0, y1: 0, x2: 0, y2: 0, w: 0, h: 0 });

// Viewport rectangle position (relative to minimap)
const viewportRect = ref({ x: 0, y: 0, width: 0, height: 0 });

// Track event handlers for cleanup
let boundHandler: (() => void) | null = null;
let layoutstopHandler: (() => void) | null = null;

// Track setTimeout for cleanup on unmount
let initTimeoutId: ReturnType<typeof setTimeout> | null = null;

// Computed style for viewport indicator
const viewportStyle = computed(() => ({
  left: `${viewportRect.value.x}px`,
  top: `${viewportRect.value.y}px`,
  width: `${viewportRect.value.width}px`,
  height: `${viewportRect.value.height}px`,
}));

/**
 * Draws simplified nodes on the canvas minimap.
 */
function drawMinimap() {
  const canvas = canvasRef.value;
  const cy = props.cy;
  if (!canvas || !cy) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Clear canvas
  ctx.clearRect(0, 0, props.width, props.height);

  // Get bounding box of all elements
  const bb = cy.elements().boundingBox();
  if (bb.w === 0 || bb.h === 0) return;

  // Add padding to bounds
  const padding = 20;
  graphBounds.value = {
    x1: bb.x1 - padding,
    y1: bb.y1 - padding,
    x2: bb.x2 + padding,
    y2: bb.y2 + padding,
    w: bb.w + padding * 2,
    h: bb.h + padding * 2,
  };

  // Calculate scale to fit graph in minimap
  const scaleX = props.width / graphBounds.value.w;
  const scaleY = props.height / graphBounds.value.h;
  const scale = Math.min(scaleX, scaleY);

  // Center offset
  const offsetX = (props.width - graphBounds.value.w * scale) / 2;
  const offsetY = (props.height - graphBounds.value.h * scale) / 2;

  // Draw edges as thin lines
  ctx.strokeStyle = "rgba(58, 107, 92, 0.3)";
  ctx.lineWidth = 0.5;
  cy.edges().forEach((edge) => {
    const sourcePos = edge.source().position();
    const targetPos = edge.target().position();

    const x1 = (sourcePos.x - graphBounds.value.x1) * scale + offsetX;
    const y1 = (sourcePos.y - graphBounds.value.y1) * scale + offsetY;
    const x2 = (targetPos.x - graphBounds.value.x1) * scale + offsetX;
    const y2 = (targetPos.y - graphBounds.value.y1) * scale + offsetY;

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  });

  // Draw nodes as small circles
  cy.nodes().forEach((node) => {
    const pos = node.position();
    const x = (pos.x - graphBounds.value.x1) * scale + offsetX;
    const y = (pos.y - graphBounds.value.y1) * scale + offsetY;

    // Get node color from data or use default
    const nodeColor = node.data("nodeColor") || "#3a6b5c";

    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fillStyle = nodeColor;
    ctx.fill();
  });
}

/**
 * Updates the viewport rectangle position based on current pan/zoom.
 */
function updateViewportRect() {
  const cy = props.cy;
  const canvas = canvasRef.value;
  if (!cy || !canvas || graphBounds.value.w === 0) return;

  // Get current extent (visible area in graph coordinates)
  const extent = cy.extent();

  // Calculate scale
  const scaleX = props.width / graphBounds.value.w;
  const scaleY = props.height / graphBounds.value.h;
  const scale = Math.min(scaleX, scaleY);

  // Center offset
  const offsetX = (props.width - graphBounds.value.w * scale) / 2;
  const offsetY = (props.height - graphBounds.value.h * scale) / 2;

  // Transform extent to minimap coordinates
  const x = (extent.x1 - graphBounds.value.x1) * scale + offsetX;
  const y = (extent.y1 - graphBounds.value.y1) * scale + offsetY;
  const w = extent.w * scale;
  const h = extent.h * scale;

  // Clamp values to minimap bounds
  viewportRect.value = {
    x: Math.max(0, Math.min(x, props.width)),
    y: Math.max(0, Math.min(y, props.height)),
    width: Math.max(10, Math.min(w, props.width)),
    height: Math.max(10, Math.min(h, props.height)),
  };
}

/**
 * Handles click on minimap to pan the main view.
 */
function handleMinimapClick(event: MouseEvent) {
  const cy = props.cy;
  const canvas = canvasRef.value;
  if (!cy || !canvas || graphBounds.value.w === 0) return;

  // Get click position relative to canvas
  const rect = canvas.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const clickY = event.clientY - rect.top;

  // Calculate scale
  const scaleX = props.width / graphBounds.value.w;
  const scaleY = props.height / graphBounds.value.h;
  const scale = Math.min(scaleX, scaleY);

  // Center offset
  const offsetX = (props.width - graphBounds.value.w * scale) / 2;
  const offsetY = (props.height - graphBounds.value.h * scale) / 2;

  // Transform click to graph coordinates
  const graphX = (clickX - offsetX) / scale + graphBounds.value.x1;
  const graphY = (clickY - offsetY) / scale + graphBounds.value.y1;

  // Pan to position (keeps zoom level)
  const currentZoom = cy.zoom();
  const containerWidth = cy.container()?.clientWidth || 0;
  const containerHeight = cy.container()?.clientHeight || 0;

  cy.pan({
    x: containerWidth / 2 - graphX * currentZoom,
    y: containerHeight / 2 - graphY * currentZoom,
  });
}

/**
 * Sets up event listeners on the cytoscape instance.
 */
function setupEventListeners() {
  const cy = props.cy;
  if (!cy) return;

  // Remove existing handler if any
  cleanupEventListeners();

  // Handler for viewport changes
  boundHandler = () => {
    updateViewportRect();
  };

  // Handler for layout completion
  layoutstopHandler = () => {
    drawMinimap();
    updateViewportRect();
  };

  // Listen to pan, zoom, and resize events
  cy.on("pan zoom resize", boundHandler);

  // Also listen to layout done to update minimap after layout changes
  cy.on("layoutstop", layoutstopHandler);

  // Initial draw
  drawMinimap();
  updateViewportRect();
}

/**
 * Cleans up event listeners from the cytoscape instance.
 */
function cleanupEventListeners() {
  if (props.cy) {
    if (boundHandler) {
      props.cy.off("pan zoom resize", boundHandler);
      boundHandler = null;
    }
    if (layoutstopHandler) {
      props.cy.off("layoutstop", layoutstopHandler);
      layoutstopHandler = null;
    }
  }
}

// Watch for cy changes
watch(
  () => props.cy,
  (newCy) => {
    // Always clear pending init timeout first to prevent queue buildup on rapid prop changes
    if (initTimeoutId !== null) {
      clearTimeout(initTimeoutId);
      initTimeoutId = null;
    }

    if (newCy) {
      // Wait a tick for cytoscape to be fully initialized
      initTimeoutId = setTimeout(() => {
        initTimeoutId = null;
        setupEventListeners();
      }, 100);
    } else {
      cleanupEventListeners();
    }
  },
  { immediate: true }
);

// Cleanup on unmount
onUnmounted(() => {
  // Clear pending init timeout
  if (initTimeoutId !== null) {
    clearTimeout(initTimeoutId);
    initTimeoutId = null;
  }
  cleanupEventListeners();
});

/**
 * Toggles minimap visibility.
 */
function toggleVisibility() {
  isVisible.value = !isVisible.value;
}
</script>

<template>
  <div class="minimap" :class="{ 'minimap--collapsed': !isVisible }">
    <button
      class="minimap__toggle"
      :title="isVisible ? 'Hide minimap' : 'Show minimap'"
      @click="toggleVisibility"
    >
      <span class="minimap__toggle-icon">{{ isVisible ? "−" : "+" }}</span>
      <span class="minimap__toggle-label">Map</span>
    </button>

    <div v-show="isVisible" class="minimap__content">
      <canvas
        ref="canvasRef"
        class="minimap__canvas"
        :width="width"
        :height="height"
        @click="handleMinimapClick"
      />
      <div class="minimap__viewport" :style="viewportStyle" />
    </div>
  </div>
</template>

<style scoped>
.minimap {
  /* Position controlled by parent container via .mini-map-overlay class */
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 10;
}

.minimap--collapsed {
  width: auto;
}

.minimap__toggle {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  width: 100%;
  padding: 0.25rem 0.5rem;
  background: var(--color-victorian-paper-cream, #f8f5f0);
  border: none;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  cursor: pointer;
  font-size: 0.625rem;
  font-family: Georgia, serif;
  color: var(--color-victorian-ink-muted, #666);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: background-color 0.15s ease;
}

.minimap__toggle:hover {
  background: var(--color-victorian-paper-aged, #e8e1d5);
}

.minimap--collapsed .minimap__toggle {
  border-bottom: none;
}

.minimap__toggle-icon {
  font-size: 0.875rem;
  line-height: 1;
}

.minimap__content {
  position: relative;
  padding: 0.25rem;
}

.minimap__canvas {
  display: block;
  background: var(--color-victorian-paper-cream, #f8f5f0);
  cursor: pointer;
}

.minimap__viewport {
  position: absolute;
  border: 2px solid var(--color-victorian-burgundy, #722f37);
  background: rgba(114, 47, 55, 0.1);
  pointer-events: none;
  box-sizing: border-box;
}
</style>
