# Node Detail Panel Redesign - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the full-width detail panel with a floating card (for nodes) and slide-out sidebar (for edges) that maintain graph visibility.

**Architecture:** New components `NodeFloatingCard.vue` and `EdgeSidebar.vue` replace `NodeDetailPanel.vue`. Shared utilities for positioning, formatting, and animations. Selection state enhanced to support edge selection with toggle-to-close behavior.

**Tech Stack:** Vue 3 Composition API, TypeScript, Cytoscape.js, @vueuse/core (focus trap)

**Design Doc:** `docs/plans/2026-01-27-node-detail-panel-design.md`

---

## Task 0: Fix Book Fetching Bug (#1377)

**Files:**
- Investigate: `frontend/src/components/socialcircles/NodeDetailPanel.vue:79-82`
- Investigate: Backend `/books` endpoint

**Step 1: Reproduce and diagnose the bug**

Check what `book_ids` are being passed and what the API returns:

```typescript
// Add temporary logging in NodeDetailPanel.vue
console.log('Fetching books for IDs:', bookIds);
const response = await api.get<{ items: BookSummary[] }>(`/books?ids=${ids}&page_size=10`);
console.log('API response:', response.data);
```

**Step 2: Verify API endpoint supports `ids` parameter**

Run: `bmx-api GET "/books?ids=1,2,3&page_size=10"` and check if it filters correctly.

**Step 3: Fix the issue**

Based on diagnosis - likely the API doesn't support `ids` filter or uses different parameter name.

**Step 4: Commit fix**

```bash
git add frontend/src/components/socialcircles/NodeDetailPanel.vue
git commit -m "fix(social-circles): correct book fetching in detail panel

Fixes #1377"
```

---

## Task 1: Create Formatting Utilities

**Files:**
- Create: `frontend/src/utils/socialCircles/formatters.ts`
- Test: `frontend/src/utils/socialCircles/__tests__/formatters.test.ts`

**Step 1: Write failing tests**

Create `frontend/src/utils/socialCircles/__tests__/formatters.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { formatTier, calculateStrength, renderStrength, getPlaceholderImage } from '../formatters';

describe('formatTier', () => {
  it('returns Premier for TIER_1', () => {
    const result = formatTier('TIER_1');
    expect(result).toEqual({
      label: 'Premier',
      stars: 3,
      tooltip: 'Tier 1 - Premier Figure',
    });
  });

  it('returns Established for TIER_2', () => {
    const result = formatTier('TIER_2');
    expect(result.label).toBe('Established');
    expect(result.stars).toBe(2);
  });

  it('returns Known for TIER_3', () => {
    const result = formatTier('TIER_3');
    expect(result.label).toBe('Known');
    expect(result.stars).toBe(1);
  });

  it('returns Unranked for null', () => {
    const result = formatTier(null);
    expect(result.label).toBe('Unranked');
    expect(result.stars).toBe(0);
  });
});

describe('calculateStrength', () => {
  it('returns book count up to 5', () => {
    expect(calculateStrength(1)).toBe(1);
    expect(calculateStrength(3)).toBe(3);
    expect(calculateStrength(5)).toBe(5);
  });

  it('caps at 5 for counts over 5', () => {
    expect(calculateStrength(6)).toBe(5);
    expect(calculateStrength(100)).toBe(5);
  });

  it('returns 0 for 0 books', () => {
    expect(calculateStrength(0)).toBe(0);
  });
});

describe('renderStrength', () => {
  it('renders correct filled/unfilled pattern', () => {
    expect(renderStrength(0)).toBe('○○○○○');
    expect(renderStrength(3)).toBe('●●●○○');
    expect(renderStrength(5)).toBe('●●●●●');
  });
});

describe('getPlaceholderImage', () => {
  it('returns author placeholder path', () => {
    const result = getPlaceholderImage('author', 42);
    expect(result).toMatch(/\/images\/entity-placeholders\/authors\//);
    expect(result).toMatch(/\.jpg$/);
  });

  it('returns consistent image for same entity ID', () => {
    const first = getPlaceholderImage('publisher', 123);
    const second = getPlaceholderImage('publisher', 123);
    expect(first).toBe(second);
  });

  it('returns different images for different entity types', () => {
    const author = getPlaceholderImage('author', 1);
    const publisher = getPlaceholderImage('publisher', 1);
    expect(author).not.toBe(publisher);
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `npm run --prefix frontend test -- formatters.test.ts`

Expected: FAIL - module not found

**Step 3: Implement formatters**

Create `frontend/src/utils/socialCircles/formatters.ts`:

```typescript
// frontend/src/utils/socialCircles/formatters.ts

import type { NodeType } from '@/types/socialCircles';

export interface TierDisplay {
  label: string;
  stars: number;
  tooltip: string;
}

const TIER_MAP: Record<string, TierDisplay> = {
  TIER_1: { label: 'Premier', stars: 3, tooltip: 'Tier 1 - Premier Figure' },
  TIER_2: { label: 'Established', stars: 2, tooltip: 'Tier 2 - Established Figure' },
  TIER_3: { label: 'Known', stars: 1, tooltip: 'Tier 3 - Known Figure' },
};

export function formatTier(tier: string | null): TierDisplay {
  return TIER_MAP[tier ?? ''] || { label: 'Unranked', stars: 0, tooltip: 'Unranked' };
}

export function calculateStrength(sharedBooks: number): number {
  return Math.min(Math.max(sharedBooks, 0), 5);
}

export function renderStrength(strength: number, max: number = 5): string {
  const capped = Math.min(Math.max(strength, 0), max);
  const filled = '●'.repeat(capped);
  const unfilled = '○'.repeat(max - capped);
  return filled + unfilled;
}

const PLACEHOLDER_COUNTS: Record<NodeType, number> = {
  author: 4,
  publisher: 4,
  binder: 4,
};

const PLACEHOLDER_NAMES: Record<NodeType, string[]> = {
  author: [
    'generic-victorian-portrait-1.jpg',
    'generic-victorian-portrait-2.jpg',
    'generic-victorian-portrait-3.jpg',
    'generic-victorian-portrait-4.jpg',
  ],
  publisher: [
    'london-bookshop-exterior.jpg',
    'victorian-printing-press.jpg',
    'publisher-office-interior.jpg',
    'victorian-publisher-logo.jpg',
  ],
  binder: [
    'bookbinding-tools.jpg',
    'leather-workshop.jpg',
    'bindery-workbench.jpg',
    'victorian-bindery-scene.jpg',
  ],
};

export function getPlaceholderImage(type: NodeType, entityId: number): string {
  const names = PLACEHOLDER_NAMES[type];
  const index = entityId % names.length;
  return `/images/entity-placeholders/${type}s/${names[index]}`;
}
```

**Step 4: Run tests to verify they pass**

Run: `npm run --prefix frontend test -- formatters.test.ts`

Expected: PASS

**Step 5: Export from index**

Update `frontend/src/utils/socialCircles/index.ts`:

```typescript
export * from './colorPalettes';
export * from './dataTransformers';
export * from './graphAlgorithms';
export * from './layoutConfigs';
export * from './formatters';
```

**Step 6: Commit**

```bash
git add frontend/src/utils/socialCircles/formatters.ts
git add frontend/src/utils/socialCircles/__tests__/formatters.test.ts
git add frontend/src/utils/socialCircles/index.ts
git commit -m "feat(social-circles): add tier and strength formatting utilities"
```

---

## Task 2: Create Smart Positioning Utility

**Files:**
- Create: `frontend/src/utils/socialCircles/cardPositioning.ts`
- Test: `frontend/src/utils/socialCircles/__tests__/cardPositioning.test.ts`

**Step 1: Write failing tests**

Create `frontend/src/utils/socialCircles/__tests__/cardPositioning.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { getBestCardPosition } from '../cardPositioning';

describe('getBestCardPosition', () => {
  const cardSize = { width: 280, height: 400 };
  const viewport = { width: 1200, height: 800 };

  it('places card bottom-right when node is top-left', () => {
    const nodePos = { x: 100, y: 100 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('bottom-right');
    expect(result.position.x).toBeGreaterThan(nodePos.x);
    expect(result.position.y).toBeGreaterThan(nodePos.y);
  });

  it('places card bottom-left when node is top-right', () => {
    const nodePos = { x: 1100, y: 100 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('bottom-left');
    expect(result.position.x).toBeLessThan(nodePos.x);
  });

  it('places card top-right when node is bottom-left', () => {
    const nodePos = { x: 100, y: 700 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('top-right');
    expect(result.position.y).toBeLessThan(nodePos.y);
  });

  it('places card top-left when node is bottom-right', () => {
    const nodePos = { x: 1100, y: 700 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('top-left');
  });

  it('respects margin parameter', () => {
    const nodePos = { x: 600, y: 400 };
    const margin = 30;
    const result = getBestCardPosition(nodePos, cardSize, viewport, margin);
    const distanceX = Math.abs(result.position.x - nodePos.x);
    const distanceY = Math.abs(result.position.y - nodePos.y);
    expect(distanceX).toBeGreaterThanOrEqual(margin);
    expect(distanceY).toBeGreaterThanOrEqual(margin);
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `npm run --prefix frontend test -- cardPositioning.test.ts`

Expected: FAIL - module not found

**Step 3: Implement positioning utility**

Create `frontend/src/utils/socialCircles/cardPositioning.ts`:

```typescript
// frontend/src/utils/socialCircles/cardPositioning.ts

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export type Quadrant = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

interface QuadrantSpace {
  width: number;
  height: number;
}

interface PositionResult {
  position: Position;
  quadrant: Quadrant;
}

export function getBestCardPosition(
  nodePos: Position,
  cardSize: Size,
  viewport: Size,
  margin: number = 20
): PositionResult {
  // Calculate available space in each quadrant
  const quadrants: Record<Quadrant, QuadrantSpace> = {
    'top-left': {
      width: nodePos.x - margin,
      height: nodePos.y - margin,
    },
    'top-right': {
      width: viewport.width - nodePos.x - margin,
      height: nodePos.y - margin,
    },
    'bottom-left': {
      width: nodePos.x - margin,
      height: viewport.height - nodePos.y - margin,
    },
    'bottom-right': {
      width: viewport.width - nodePos.x - margin,
      height: viewport.height - nodePos.y - margin,
    },
  };

  // Score each quadrant
  const scores = (Object.entries(quadrants) as [Quadrant, QuadrantSpace][]).map(
    ([name, space]) => {
      const canFit = space.width >= cardSize.width && space.height >= cardSize.height;
      if (!canFit) return { name, score: -1 };

      let score = 0;
      // Distance from edges (higher = better)
      score += Math.min(space.width - cardSize.width, 100);
      score += Math.min(space.height - cardSize.height, 100);
      // Prefer right (reading order)
      if (name.includes('right')) score += 20;
      // Prefer bottom (natural flow)
      if (name.includes('bottom')) score += 10;

      return { name, score };
    }
  );

  // Pick best quadrant (fallback to bottom-right if none fit)
  const best = scores.reduce((a, b) => (a.score > b.score ? a : b));
  const quadrant: Quadrant = best.score >= 0 ? best.name : 'bottom-right';

  // Calculate position with margin
  const position: Position = {
    x: quadrant.includes('right')
      ? nodePos.x + margin
      : nodePos.x - cardSize.width - margin,
    y: quadrant.includes('bottom')
      ? nodePos.y + margin
      : nodePos.y - cardSize.height - margin,
  };

  // Clamp to viewport bounds
  position.x = Math.max(margin, Math.min(position.x, viewport.width - cardSize.width - margin));
  position.y = Math.max(margin, Math.min(position.y, viewport.height - cardSize.height - margin));

  return { position, quadrant };
}
```

**Step 4: Run tests to verify they pass**

Run: `npm run --prefix frontend test -- cardPositioning.test.ts`

Expected: PASS

**Step 5: Export from index**

Update `frontend/src/utils/socialCircles/index.ts` to add:

```typescript
export * from './cardPositioning';
```

**Step 6: Commit**

```bash
git add frontend/src/utils/socialCircles/cardPositioning.ts
git add frontend/src/utils/socialCircles/__tests__/cardPositioning.test.ts
git add frontend/src/utils/socialCircles/index.ts
git commit -m "feat(social-circles): add smart card positioning utility"
```

---

## Task 3: Add Design System Constants

**Files:**
- Modify: `frontend/src/constants/socialCircles.ts`

**Step 1: Add color and animation constants**

Add to `frontend/src/constants/socialCircles.ts`:

```typescript
// =============================================================================
// Detail Panel Colors (from design doc)
// =============================================================================

export const PANEL_COLORS = {
  // Backgrounds
  cardBg: '#F5F1E8',
  sidebarBg: '#FAF8F3',
  skeletonBg: '#E8E4DB',

  // Text
  textPrimary: '#2C2416',
  textSecondary: '#5C5446',
  textMuted: '#8B8579',

  // Interactive
  accentGold: '#B8860B',
  hover: '#8B4513',
  selected: '#2C5F77',
  link: '#6B4423',

  // Borders
  border: '#D4CFC4',
  borderStrong: '#A69F92',

  // Entity accents
  author: '#7B4B94',
  publisher: '#2C5F77',
  binder: '#8B4513',
} as const;

// =============================================================================
// Panel Animation Config
// =============================================================================

export const PANEL_ANIMATION = {
  duration: 200,
  // Subtle spring easing for Victorian elegance
  easing: 'cubic-bezier(0.4, 0.0, 0.2, 1)',
  easingOut: 'cubic-bezier(0.4, 0.0, 1, 1)',
} as const;

// =============================================================================
// Panel Dimensions
// =============================================================================

export const PANEL_DIMENSIONS = {
  card: {
    width: 280,
    maxHeight: 400,
    margin: 20,
  },
  sidebar: {
    widthPercent: 35, // 30-40% as per design
    minWidth: 320,
    maxWidth: 500,
  },
} as const;

// =============================================================================
// Responsive Breakpoints
// =============================================================================

export const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
} as const;

// =============================================================================
// Touch Targets (Accessibility)
// =============================================================================

export const TOUCH_TARGETS = {
  minSize: 44, // iOS guideline
  minSizeAndroid: 48, // Material Design
} as const;
```

**Step 2: Commit**

```bash
git add frontend/src/constants/socialCircles.ts
git commit -m "feat(social-circles): add panel design system constants"
```

---

## Task 4: Enhance Selection State for Toggle Behavior

**Files:**
- Modify: `frontend/src/composables/socialcircles/useNetworkSelection.ts`
- Test: `frontend/src/composables/socialcircles/__tests__/useNetworkSelection.test.ts`

**Step 1: Write tests for toggle behavior**

Create `frontend/src/composables/socialcircles/__tests__/useNetworkSelection.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { useNetworkSelection } from '../useNetworkSelection';
import type { ApiNode, ApiEdge, NodeId, EdgeId } from '@/types/socialCircles';

describe('useNetworkSelection toggle behavior', () => {
  const mockNodes: ApiNode[] = [
    { id: 'author:1' as NodeId, entity_id: 1, name: 'Author 1', type: 'author', book_count: 5, book_ids: [] },
    { id: 'publisher:1' as NodeId, entity_id: 1, name: 'Publisher 1', type: 'publisher', book_count: 3, book_ids: [] },
  ];

  const mockEdges: ApiEdge[] = [
    { id: 'e:author:1:publisher:1' as EdgeId, source: 'author:1' as NodeId, target: 'publisher:1' as NodeId, type: 'publisher', strength: 3 },
  ];

  let selection: ReturnType<typeof useNetworkSelection>;

  beforeEach(() => {
    selection = useNetworkSelection();
    selection.setNodesAndEdges(mockNodes, mockEdges);
  });

  it('toggleSelectNode closes panel but keeps highlight when clicking same node', () => {
    // Select node
    selection.selectNode('author:1' as NodeId);
    expect(selection.selection.value.selectedNodeId).toBe('author:1');
    expect(selection.isPanelOpen.value).toBe(true);

    // Toggle same node - panel closes, selection stays highlighted
    selection.toggleSelectNode('author:1' as NodeId);
    expect(selection.isPanelOpen.value).toBe(false);
    expect(selection.selection.value.selectedNodeId).toBe('author:1'); // Still selected
    expect(selection.selection.value.highlightedNodeIds.size).toBeGreaterThan(0); // Still highlighted
  });

  it('toggleSelectNode opens panel when clicking same node again', () => {
    selection.selectNode('author:1' as NodeId);
    selection.toggleSelectNode('author:1' as NodeId); // Close
    selection.toggleSelectNode('author:1' as NodeId); // Open again
    expect(selection.isPanelOpen.value).toBe(true);
  });

  it('selectNode always opens panel and switches selection', () => {
    selection.selectNode('author:1' as NodeId);
    selection.toggleSelectNode('author:1' as NodeId); // Close panel

    // Select different node - should open and switch
    selection.selectNode('publisher:1' as NodeId);
    expect(selection.selection.value.selectedNodeId).toBe('publisher:1');
    expect(selection.isPanelOpen.value).toBe(true);
  });

  it('clearSelection clears both selection and panel state', () => {
    selection.selectNode('author:1' as NodeId);
    selection.clearSelection();

    expect(selection.selection.value.selectedNodeId).toBeNull();
    expect(selection.isPanelOpen.value).toBe(false);
    expect(selection.selection.value.highlightedNodeIds.size).toBe(0);
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `npm run --prefix frontend test -- useNetworkSelection.test.ts`

Expected: FAIL - `isPanelOpen` and `toggleSelectNode` not found

**Step 3: Add toggle behavior to useNetworkSelection**

Modify `frontend/src/composables/socialcircles/useNetworkSelection.ts`:

```typescript
/**
 * useNetworkSelection - Manages node/edge selection and highlighting.
 * Enhanced with toggle behavior: clicking same item closes panel but keeps highlight.
 */

import { ref, computed, readonly } from "vue";
import type { NodeId, EdgeId, SelectionState, ApiNode, ApiEdge } from "@/types/socialCircles";
import { DEFAULT_SELECTION_STATE } from "@/types/socialCircles";

export function useNetworkSelection() {
  const selection = ref<SelectionState>({ ...DEFAULT_SELECTION_STATE });
  const isPanelOpen = ref(false);

  // Store nodes and edges for lookup
  const nodesMap = ref<Map<NodeId, ApiNode>>(new Map());
  const edgesMap = ref<Map<EdgeId, ApiEdge>>(new Map());

  // Computed
  const selectedNode = computed(() => {
    const id = selection.value.selectedNodeId;
    return id ? nodesMap.value.get(id) || null : null;
  });

  const selectedEdge = computed(() => {
    const id = selection.value.selectedEdgeId;
    return id ? edgesMap.value.get(id) || null : null;
  });

  const isNodeSelected = computed(() => selection.value.selectedNodeId !== null);
  const isEdgeSelected = computed(() => selection.value.selectedEdgeId !== null);

  // Computed arrays for highlighted elements (ensures proper reactivity)
  const highlightedNodeIds = computed(() => Array.from(selection.value.highlightedNodeIds));
  const highlightedEdgeIds = computed(() => Array.from(selection.value.highlightedEdgeIds));

  // Actions
  function setNodesAndEdges(nodes: ApiNode[], edges: ApiEdge[]) {
    nodesMap.value.clear();
    edgesMap.value.clear();
    nodes.forEach((n) => nodesMap.value.set(n.id, n));
    edges.forEach((e) => edgesMap.value.set(e.id, e));
  }

  function updateHighlightsForNode(nodeId: NodeId) {
    const connectedNodeIds = new Set<NodeId>();
    const connectedEdgeIds = new Set<EdgeId>();

    edgesMap.value.forEach((edge, edgeId) => {
      if (edge.source === nodeId || edge.target === nodeId) {
        connectedEdgeIds.add(edgeId);
        connectedNodeIds.add(edge.source as NodeId);
        connectedNodeIds.add(edge.target as NodeId);
      }
    });

    selection.value.highlightedNodeIds = connectedNodeIds;
    selection.value.highlightedEdgeIds = connectedEdgeIds;
  }

  function selectNode(nodeId: NodeId | null) {
    selection.value.selectedEdgeId = null; // Clear edge selection

    if (nodeId) {
      selection.value.selectedNodeId = nodeId;
      updateHighlightsForNode(nodeId);
      isPanelOpen.value = true;
    } else {
      selection.value.selectedNodeId = null;
      selection.value.highlightedNodeIds = new Set();
      selection.value.highlightedEdgeIds = new Set();
      isPanelOpen.value = false;
    }
  }

  /**
   * Toggle selection: if same node clicked, close panel but keep highlight.
   * If different node, switch selection and open panel.
   */
  function toggleSelectNode(nodeId: NodeId) {
    if (selection.value.selectedNodeId === nodeId) {
      // Same node - toggle panel open/closed, keep highlight
      isPanelOpen.value = !isPanelOpen.value;
    } else {
      // Different node - switch selection and open
      selectNode(nodeId);
    }
  }

  function selectEdge(edgeId: EdgeId | null) {
    selection.value.selectedNodeId = null; // Clear node selection

    if (edgeId) {
      const edge = edgesMap.value.get(edgeId);
      if (edge) {
        selection.value.selectedEdgeId = edgeId;
        const connectedNodeIds = new Set<NodeId>([edge.source as NodeId, edge.target as NodeId]);
        const connectedEdgeIds = new Set<EdgeId>([edgeId]);

        selection.value.highlightedNodeIds = connectedNodeIds;
        selection.value.highlightedEdgeIds = connectedEdgeIds;
        isPanelOpen.value = true;
      }
    } else {
      selection.value.selectedEdgeId = null;
      selection.value.highlightedNodeIds = new Set();
      selection.value.highlightedEdgeIds = new Set();
      isPanelOpen.value = false;
    }
  }

  /**
   * Toggle edge selection: if same edge clicked, close panel but keep highlight.
   */
  function toggleSelectEdge(edgeId: EdgeId) {
    if (selection.value.selectedEdgeId === edgeId) {
      isPanelOpen.value = !isPanelOpen.value;
    } else {
      selectEdge(edgeId);
    }
  }

  function clearSelection() {
    selection.value.selectedNodeId = null;
    selection.value.selectedEdgeId = null;
    selection.value.highlightedNodeIds = new Set();
    selection.value.highlightedEdgeIds = new Set();
    isPanelOpen.value = false;
  }

  /**
   * Close panel only (keep selection highlighted for reference).
   */
  function closePanel() {
    isPanelOpen.value = false;
  }

  function setHoveredNode(nodeId: NodeId | null) {
    selection.value.hoveredNodeId = nodeId;
  }

  function setHoveredEdge(edgeId: EdgeId | null) {
    selection.value.hoveredEdgeId = edgeId;
  }

  function isNodeHighlighted(nodeId: NodeId): boolean {
    return selection.value.highlightedNodeIds.has(nodeId);
  }

  function isEdgeHighlighted(edgeId: EdgeId): boolean {
    return selection.value.highlightedEdgeIds.has(edgeId);
  }

  return {
    selection: readonly(selection),
    isPanelOpen: readonly(isPanelOpen),
    selectedNode,
    selectedEdge,
    isNodeSelected,
    isEdgeSelected,
    highlightedNodeIds,
    highlightedEdgeIds,
    setNodesAndEdges,
    selectNode,
    toggleSelectNode,
    selectEdge,
    toggleSelectEdge,
    clearSelection,
    closePanel,
    setHoveredNode,
    setHoveredEdge,
    isNodeHighlighted,
    isEdgeHighlighted,
  };
}
```

**Step 4: Run tests to verify they pass**

Run: `npm run --prefix frontend test -- useNetworkSelection.test.ts`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/composables/socialcircles/useNetworkSelection.ts
git add frontend/src/composables/socialcircles/__tests__/useNetworkSelection.test.ts
git commit -m "feat(social-circles): add toggle behavior to selection state"
```

---

## Task 5: Create NodeFloatingCard Component

**Files:**
- Create: `frontend/src/components/socialcircles/NodeFloatingCard.vue`

**Step 1: Create the component**

Create `frontend/src/components/socialcircles/NodeFloatingCard.vue`:

```vue
<!-- frontend/src/components/socialcircles/NodeFloatingCard.vue -->
<script setup lang="ts">
/**
 * NodeFloatingCard - Floating card for entity summary.
 * Smart positioned, shows first 5 connections, links to edge details.
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useFocusTrap } from '@vueuse/integrations/useFocusTrap';
import type { ApiNode, ApiEdge, NodeId, EdgeId, ConnectionType } from '@/types/socialCircles';
import { formatTier, getPlaceholderImage } from '@/utils/socialCircles/formatters';
import { getBestCardPosition, type Position, type Size } from '@/utils/socialCircles/cardPositioning';
import { PANEL_DIMENSIONS, PANEL_ANIMATION } from '@/constants/socialCircles';

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
  if (!props.node) return '';
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
      const otherNode = props.nodes.find(n => n.id === otherNodeId);
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
  return props.edges.filter(
    e => e.source === props.node!.id || e.target === props.node!.id
  ).length;
});

const remainingConnections = computed(() => {
  return Math.max(0, totalConnections.value - connections.value.length);
});

// Connection type icons
function getConnectionIcon(type: ConnectionType): string {
  const icons: Record<ConnectionType, string> = {
    publisher: '📚',
    shared_publisher: '🤝',
    binder: '🪡',
  };
  return icons[type] || '→';
}

// Keyboard handling
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close');
  }
}

// Focus trap management
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    setTimeout(() => activate(), PANEL_ANIMATION.duration);
  } else {
    deactivate();
  }
});

// Global escape listener
onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
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
            <span aria-hidden="true">{{ '★'.repeat(tierDisplay.stars) }}{{ '☆'.repeat(3 - tierDisplay.stars) }}</span>
          </div>
          <p v-if="node.birth_year || node.death_year" class="node-floating-card__dates">
            {{ node.birth_year || '?' }} – {{ node.death_year || '?' }}
          </p>
          <p v-if="node.era" class="node-floating-card__era">
            {{ node.era.replace('_', ' ') }}
          </p>
        </div>
        <button
          class="node-floating-card__close"
          aria-label="Close"
          @click="emit('close')"
        >
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
          <span v-if="remainingConnections > 0">(showing {{ connections.length }} of {{ totalConnections }})</span>
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
              <span class="node-floating-card__connection-icon">{{ getConnectionIcon(conn.connectionType) }}</span>
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
        <button
          class="node-floating-card__profile-button"
          @click="emit('viewProfile', node.id)"
        >
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
  background: var(--color-card-bg, #F5F1E8);
  border: 1px solid var(--color-border, #D4CFC4);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2000;
}

.node-floating-card--author {
  border-top: 3px solid var(--color-author, #7B4B94);
}

.node-floating-card--publisher {
  border-top: 3px solid var(--color-publisher, #2C5F77);
}

.node-floating-card--binder {
  border-top: 3px solid var(--color-binder, #8B4513);
}

.node-floating-card__header {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #D4CFC4);
}

.node-floating-card__image {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
  background: var(--color-skeleton-bg, #E8E4DB);
}

.node-floating-card__info {
  flex: 1;
  min-width: 0;
}

.node-floating-card__name {
  font-size: 1rem;
  font-weight: 600;
  font-family: Georgia, serif;
  color: var(--color-text-primary, #2C2416);
  margin: 0;
  line-height: 1.3;
}

.node-floating-card__tier {
  color: var(--color-accent-gold, #B8860B);
  font-size: 0.875rem;
  margin-top: 2px;
}

.node-floating-card__dates,
.node-floating-card__era {
  font-size: 0.75rem;
  color: var(--color-text-secondary, #5C5446);
  margin: 2px 0 0;
}

.node-floating-card__close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--color-text-muted, #8B8579);
  cursor: pointer;
  padding: 4px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-floating-card__close:hover {
  color: var(--color-text-primary, #2C2416);
}

.node-floating-card__stats {
  padding: 8px 16px;
  font-size: 0.75rem;
  color: var(--color-text-secondary, #5C5446);
  display: flex;
  gap: 6px;
  border-bottom: 1px solid var(--color-border, #D4CFC4);
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
  color: var(--color-text-muted, #8B8579);
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
  transition: background 150ms ease-out, transform 150ms ease-out;
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
  color: var(--color-text-primary, #2C2416);
}

.node-floating-card__connection-type {
  font-size: 0.75rem;
  color: var(--color-text-muted, #8B8579);
}

.node-floating-card__more-link {
  display: block;
  margin-top: 8px;
  padding: 4px 0;
  background: none;
  border: none;
  font-size: 0.75rem;
  color: var(--color-link, #6B4423);
  cursor: pointer;
  text-decoration: underline;
}

.node-floating-card__more-link:hover {
  color: var(--color-hover, #8B4513);
}

.node-floating-card__empty {
  padding: 16px;
  font-size: 0.875rem;
  color: var(--color-text-muted, #8B8579);
  font-style: italic;
}

.node-floating-card__footer {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border, #D4CFC4);
}

.node-floating-card__profile-button {
  width: 100%;
  padding: 10px 16px;
  background: var(--color-accent-gold, #B8860B);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 150ms ease-out, transform 150ms ease-out;
}

.node-floating-card__profile-button:hover {
  background: var(--color-hover, #8B4513);
  transform: translateY(-1px);
}

/* Transitions */
.card-enter-active {
  transition: transform 200ms cubic-bezier(0.4, 0.0, 0.2, 1),
              opacity 200ms ease-out;
}

.card-leave-active {
  transition: transform 150ms cubic-bezier(0.4, 0.0, 1, 1),
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
```

**Step 2: Verify component compiles**

Run: `npm run --prefix frontend type-check`

Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add frontend/src/components/socialcircles/NodeFloatingCard.vue
git commit -m "feat(social-circles): create NodeFloatingCard component"
```

---

## Task 6: Create EdgeSidebar Component

**Files:**
- Create: `frontend/src/components/socialcircles/EdgeSidebar.vue`

**Step 1: Create the component**

Create `frontend/src/components/socialcircles/EdgeSidebar.vue`:

```vue
<!-- frontend/src/components/socialcircles/EdgeSidebar.vue -->
<script setup lang="ts">
/**
 * EdgeSidebar - Slide-out sidebar for edge/connection details.
 * Shows relationship between two entities with shared books.
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useFocusTrap } from '@vueuse/integrations/useFocusTrap';
import { api } from '@/services/api';
import type { ApiNode, ApiEdge, NodeId, ConnectionType } from '@/types/socialCircles';
import { formatTier, getPlaceholderImage, renderStrength, calculateStrength } from '@/utils/socialCircles/formatters';
import { PANEL_ANIMATION } from '@/constants/socialCircles';

interface Props {
  edge: ApiEdge | null;
  nodes: readonly ApiNode[];
  isOpen: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  selectNode: [nodeId: NodeId];
}>();

const router = useRouter();
const sidebarRef = ref<HTMLElement | null>(null);
const { activate, deactivate } = useFocusTrap(sidebarRef, { immediate: false });
const isPinned = ref(false);

// Source and target nodes
const sourceNode = computed(() => {
  if (!props.edge) return null;
  return props.nodes.find(n => n.id === props.edge!.source) || null;
});

const targetNode = computed(() => {
  if (!props.edge) return null;
  return props.nodes.find(n => n.id === props.edge!.target) || null;
});

// Connection type display
const connectionLabel = computed(() => {
  if (!props.edge) return '';
  const labels: Record<ConnectionType, string> = {
    publisher: 'Published together',
    shared_publisher: 'Shared Publisher',
    binder: 'Bound works',
  };
  return labels[props.edge.type];
});

// Strength display
const strengthDisplay = computed(() => {
  if (!props.edge) return '';
  const strength = calculateStrength(props.edge.shared_book_ids?.length || props.edge.strength);
  return renderStrength(strength);
});

const sharedBookCount = computed(() => {
  return props.edge?.shared_book_ids?.length || 0;
});

// Fetch shared books
interface BookSummary {
  id: number;
  title: string;
  year?: number;
}

const sharedBooks = ref<BookSummary[]>([]);
const isLoadingBooks = ref(false);

watch(
  () => ({ isOpen: props.isOpen, bookIds: props.edge?.shared_book_ids }),
  async ({ isOpen, bookIds }) => {
    if (!isOpen || !bookIds || bookIds.length === 0) {
      sharedBooks.value = [];
      return;
    }

    isLoadingBooks.value = true;
    try {
      const ids = bookIds.slice(0, 20).join(',');
      const response = await api.get<{ items: BookSummary[] }>(`/books?ids=${ids}&page_size=20`);
      sharedBooks.value = response.data.items || [];
    } catch (error) {
      console.error('Failed to fetch shared books:', error);
      sharedBooks.value = bookIds.slice(0, 20).map(id => ({ id, title: `Book #${id}` }));
    } finally {
      isLoadingBooks.value = false;
    }
  },
  { immediate: true }
);

// Navigate to book
function viewBook(bookId: number) {
  void router.push({ name: 'book-detail', params: { id: bookId } });
}

// Entity images
function getEntityImage(node: ApiNode | null): string {
  if (!node) return '';
  return getPlaceholderImage(node.type, node.entity_id);
}

// Keyboard handling
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close');
  }
}

// Focus trap management
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    setTimeout(() => activate(), PANEL_ANIMATION.duration);
  } else {
    deactivate();
  }
});

onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
  deactivate();
});
</script>

<template>
  <Transition name="sidebar">
    <aside
      v-if="isOpen && edge && sourceNode && targetNode"
      ref="sidebarRef"
      class="edge-sidebar"
      :class="`edge-sidebar--${edge.type}`"
      role="dialog"
      aria-modal="false"
      :aria-label="`Connection between ${sourceNode.name} and ${targetNode.name}`"
    >
      <!-- Header (sticky) -->
      <header class="edge-sidebar__header">
        <div class="edge-sidebar__entities">
          <!-- Source Entity -->
          <button
            class="edge-sidebar__entity"
            @click="emit('selectNode', sourceNode.id)"
          >
            <img
              :src="getEntityImage(sourceNode)"
              :alt="sourceNode.name"
              class="edge-sidebar__entity-image"
              loading="lazy"
            />
            <span class="edge-sidebar__entity-name">{{ sourceNode.name }}</span>
            <span class="edge-sidebar__entity-type">({{ sourceNode.type }})</span>
          </button>

          <!-- Connection indicator -->
          <div class="edge-sidebar__connection-arrow">
            {{ edge.type === 'shared_publisher' ? '↔' : '→' }}
          </div>

          <!-- Target Entity -->
          <button
            class="edge-sidebar__entity"
            @click="emit('selectNode', targetNode.id)"
          >
            <img
              :src="getEntityImage(targetNode)"
              :alt="targetNode.name"
              class="edge-sidebar__entity-image"
              loading="lazy"
            />
            <span class="edge-sidebar__entity-name">{{ targetNode.name }}</span>
            <span class="edge-sidebar__entity-type">({{ targetNode.type }})</span>
          </button>
        </div>

        <div class="edge-sidebar__actions">
          <button
            class="edge-sidebar__pin"
            :class="{ 'edge-sidebar__pin--active': isPinned }"
            :aria-pressed="isPinned"
            aria-label="Pin sidebar"
            @click="isPinned = !isPinned"
          >
            📌
          </button>
          <button
            class="edge-sidebar__close"
            aria-label="Close"
            @click="emit('close')"
          >
            ✕
          </button>
        </div>
      </header>

      <!-- Connection Info -->
      <section class="edge-sidebar__connection-info">
        <h3 class="edge-sidebar__connection-label">CONNECTION: {{ connectionLabel }}</h3>
        <div class="edge-sidebar__strength">
          <span class="edge-sidebar__strength-dots">{{ strengthDisplay }}</span>
          <span class="edge-sidebar__strength-count">({{ sharedBookCount }} works)</span>
        </div>
      </section>

      <!-- Shared Books (scrollable) -->
      <section class="edge-sidebar__content">
        <h4 class="edge-sidebar__section-title">
          {{ edge.type === 'binder' ? 'Bound Books' : 'Shared Books' }}
        </h4>

        <div v-if="isLoadingBooks" class="edge-sidebar__loading">
          <div class="edge-sidebar__skeleton-book"></div>
          <div class="edge-sidebar__skeleton-book"></div>
          <div class="edge-sidebar__skeleton-book"></div>
        </div>

        <ul v-else-if="sharedBooks.length > 0" class="edge-sidebar__book-list">
          <li
            v-for="book in sharedBooks"
            :key="book.id"
            class="edge-sidebar__book-item"
          >
            <button
              class="edge-sidebar__book-button"
              @click="viewBook(book.id)"
            >
              <span class="edge-sidebar__book-icon">📖</span>
              <span class="edge-sidebar__book-title">{{ book.title }}</span>
              <span v-if="book.year" class="edge-sidebar__book-year">({{ book.year }})</span>
            </button>
          </li>
        </ul>

        <p v-else class="edge-sidebar__empty">
          No shared books found in your collection.
        </p>
      </section>

      <!-- Footer (sticky) -->
      <footer class="edge-sidebar__footer">
        <button
          class="edge-sidebar__view-button"
          @click="emit('selectNode', sourceNode.id)"
        >
          View {{ sourceNode.type === 'author' ? 'Author' : sourceNode.type }}
        </button>
        <button
          class="edge-sidebar__view-button"
          @click="emit('selectNode', targetNode.id)"
        >
          View {{ targetNode.type === 'publisher' ? 'Publisher' : targetNode.type === 'binder' ? 'Bindery' : targetNode.type }}
        </button>
      </footer>
    </aside>
  </Transition>
</template>

<style scoped>
.edge-sidebar {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 35%;
  min-width: 320px;
  max-width: 500px;
  background: var(--color-sidebar-bg, #FAF8F3);
  border-left: 1px solid var(--color-border, #D4CFC4);
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 3000;
}

.edge-sidebar--publisher {
  border-top: 3px solid var(--color-accent-gold, #B8860B);
}

.edge-sidebar--shared_publisher {
  border-top: 3px solid var(--color-publisher, #2C5F77);
}

.edge-sidebar--binder {
  border-top: 3px solid var(--color-binder, #8B4513);
}

.edge-sidebar__header {
  position: sticky;
  top: 0;
  padding: 16px;
  background: var(--color-sidebar-bg, #FAF8F3);
  border-bottom: 1px solid var(--color-border, #D4CFC4);
  z-index: 1;
}

.edge-sidebar__entities {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.edge-sidebar__entity {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  background: none;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 150ms ease-out;
  flex: 1;
}

.edge-sidebar__entity:hover {
  background: rgba(184, 134, 11, 0.1);
}

.edge-sidebar__entity-image {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
  background: var(--color-skeleton-bg, #E8E4DB);
}

.edge-sidebar__entity-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary, #2C2416);
  text-align: center;
}

.edge-sidebar__entity-type {
  font-size: 0.75rem;
  color: var(--color-text-muted, #8B8579);
}

.edge-sidebar__connection-arrow {
  font-size: 1.5rem;
  color: var(--color-text-muted, #8B8579);
}

.edge-sidebar__actions {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
}

.edge-sidebar__pin,
.edge-sidebar__close {
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--color-text-muted, #8B8579);
  cursor: pointer;
  padding: 4px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.edge-sidebar__pin:hover,
.edge-sidebar__close:hover {
  color: var(--color-text-primary, #2C2416);
}

.edge-sidebar__pin--active {
  color: var(--color-accent-gold, #B8860B);
}

.edge-sidebar__connection-info {
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #D4CFC4);
}

.edge-sidebar__connection-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-secondary, #5C5446);
  margin: 0 0 8px;
}

.edge-sidebar__strength {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edge-sidebar__strength-dots {
  font-size: 1rem;
  color: var(--color-accent-gold, #B8860B);
  letter-spacing: 2px;
}

.edge-sidebar__strength-count {
  font-size: 0.875rem;
  color: var(--color-text-muted, #8B8579);
}

.edge-sidebar__content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.edge-sidebar__section-title {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #8B8579);
  margin: 0 0 12px;
}

.edge-sidebar__loading {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.edge-sidebar__skeleton-book {
  height: 48px;
  background: linear-gradient(90deg, var(--color-skeleton-bg, #E8E4DB) 25%, #f0ede5 50%, var(--color-skeleton-bg, #E8E4DB) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.edge-sidebar__book-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.edge-sidebar__book-item {
  margin-bottom: 4px;
}

.edge-sidebar__book-button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  min-height: 48px;
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition: background 150ms ease-out;
}

.edge-sidebar__book-button:hover {
  background: rgba(184, 134, 11, 0.1);
}

.edge-sidebar__book-button:hover .edge-sidebar__book-title {
  text-decoration: underline;
  color: var(--color-accent-gold, #B8860B);
}

.edge-sidebar__book-icon {
  font-size: 1rem;
}

.edge-sidebar__book-title {
  flex: 1;
  font-size: 0.875rem;
  color: var(--color-link, #6B4423);
  font-style: italic;
}

.edge-sidebar__book-year {
  font-size: 0.75rem;
  color: var(--color-text-muted, #8B8579);
}

.edge-sidebar__empty {
  font-size: 0.875rem;
  color: var(--color-text-muted, #8B8579);
  font-style: italic;
}

.edge-sidebar__footer {
  position: sticky;
  bottom: 0;
  padding: 16px;
  background: var(--color-sidebar-bg, #FAF8F3);
  border-top: 1px solid var(--color-border, #D4CFC4);
  display: flex;
  gap: 12px;
}

.edge-sidebar__view-button {
  flex: 1;
  padding: 10px 16px;
  background: white;
  color: var(--color-text-primary, #2C2416);
  border: 1px solid var(--color-border, #D4CFC4);
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 150ms ease-out, border-color 150ms ease-out;
}

.edge-sidebar__view-button:hover {
  background: var(--color-card-bg, #F5F1E8);
  border-color: var(--color-accent-gold, #B8860B);
}

/* Transitions */
.sidebar-enter-active {
  transition: transform 200ms cubic-bezier(0.4, 0.0, 0.2, 1);
}

.sidebar-leave-active {
  transition: transform 150ms cubic-bezier(0.4, 0.0, 1, 1);
}

.sidebar-enter-from,
.sidebar-leave-to {
  transform: translateX(100%);
}

/* Mobile: full width */
@media (max-width: 768px) {
  .edge-sidebar {
    width: 100%;
    max-width: none;
  }
}
</style>
```

**Step 2: Verify component compiles**

Run: `npm run --prefix frontend type-check`

Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add frontend/src/components/socialcircles/EdgeSidebar.vue
git commit -m "feat(social-circles): create EdgeSidebar component"
```

---

## Task 7: Integrate New Components into SocialCirclesView

**Files:**
- Modify: `frontend/src/views/SocialCirclesView.vue`
- Modify: `frontend/src/composables/socialcircles/useSocialCircles.ts`

**Step 1: Update useSocialCircles to expose new selection methods**

Ensure `useSocialCircles.ts` exports the new selection methods from Task 4. Verify these are available:
- `toggleSelectNode`
- `toggleSelectEdge`
- `closePanel`
- `isPanelOpen`
- `selectedEdge`

**Step 2: Update SocialCirclesView to use new components**

Replace `NodeDetailPanel` usage with `NodeFloatingCard` and `EdgeSidebar`. The integration requires:

1. Import new components
2. Get node position from Cytoscape when clicked
3. Pass viewport size
4. Wire up event handlers

This task is complex and may require multiple sub-steps. See design doc for full integration requirements.

**Step 3: Verify in browser**

Run: `npm run --prefix frontend dev`

Navigate to `/social-circles`, click nodes and edges, verify:
- Floating card appears with smart positioning
- Sidebar slides in from right
- Toggle behavior works
- ESC closes panels

**Step 4: Commit**

```bash
git add frontend/src/views/SocialCirclesView.vue
git add frontend/src/composables/socialcircles/useSocialCircles.ts
git commit -m "feat(social-circles): integrate NodeFloatingCard and EdgeSidebar"
```

---

## Task 8: Add Placeholder Images

**Files:**
- Create: `frontend/public/images/entity-placeholders/authors/*.jpg`
- Create: `frontend/public/images/entity-placeholders/publishers/*.jpg`
- Create: `frontend/public/images/entity-placeholders/binders/*.jpg`

**Step 1: Create directory structure**

```bash
mkdir -p frontend/public/images/entity-placeholders/authors
mkdir -p frontend/public/images/entity-placeholders/publishers
mkdir -p frontend/public/images/entity-placeholders/binders
```

**Step 2: Source and add placeholder images**

Download public domain Victorian-era images from:
- Library of Congress Digital Collections
- British Library Flickr Commons
- Wikimedia Commons Victorian collections

Optimize to:
- 200x200px for cards
- WebP format with JPEG fallback
- <50KB per image

**Step 3: Add images to directories**

Add 4 images per category as specified in design doc.

**Step 4: Commit**

```bash
git add frontend/public/images/entity-placeholders/
git commit -m "feat(social-circles): add Victorian placeholder images"
```

---

## Task 9: Remove Old NodeDetailPanel

**Files:**
- Delete: `frontend/src/components/socialcircles/NodeDetailPanel.vue`
- Modify: Any files importing NodeDetailPanel

**Step 1: Search for usages**

```bash
grep -r "NodeDetailPanel" frontend/src/
```

**Step 2: Remove imports and usages**

Update all files to remove NodeDetailPanel references.

**Step 3: Delete the file**

```bash
rm frontend/src/components/socialcircles/NodeDetailPanel.vue
```

**Step 4: Verify build**

Run: `npm run --prefix frontend type-check`
Run: `npm run --prefix frontend build`

Expected: No errors

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor(social-circles): remove old NodeDetailPanel component"
```

---

## Task 10: Final Validation

**Step 1: Run all linters**

```bash
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check
```

Fix any issues.

**Step 2: Run tests**

```bash
npm run --prefix frontend test
```

Ensure all tests pass.

**Step 3: Manual testing checklist**

- [ ] Click node → floating card appears with smart positioning
- [ ] Click same node → card closes, selection stays highlighted
- [ ] Click different node → card moves to new node
- [ ] Click edge → sidebar slides in from right
- [ ] Click same edge → sidebar closes, edge stays highlighted
- [ ] Click outside (graph background) → panels close
- [ ] ESC key → panels close
- [ ] Tab through card → focus trap works
- [ ] Connection in card → clicking opens edge sidebar
- [ ] Book in sidebar → clicking navigates to book page
- [ ] Mobile (<768px) → card at bottom, sidebar full width
- [ ] Tier displays as stars, not "TIER_1"
- [ ] Placeholder images load correctly

**Step 4: Commit any final fixes**

```bash
git add -A
git commit -m "fix(social-circles): address review feedback"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 0 | Fix book fetching bug #1377 | NodeDetailPanel.vue |
| 1 | Create formatting utilities | formatters.ts |
| 2 | Create positioning utility | cardPositioning.ts |
| 3 | Add design system constants | socialCircles.ts |
| 4 | Enhance selection state | useNetworkSelection.ts |
| 5 | Create NodeFloatingCard | NodeFloatingCard.vue |
| 6 | Create EdgeSidebar | EdgeSidebar.vue |
| 7 | Integrate into view | SocialCirclesView.vue |
| 8 | Add placeholder images | public/images/ |
| 9 | Remove old component | NodeDetailPanel.vue |
| 10 | Final validation | All files |

---

---

## User Feedback Addendum (9.5/10 Rating)

### Issue References

User feedback incorporated via GitHub issues:
- #1378: Component tests for NodeDetailCard and EdgeDetailSidebar
- #1379: Task 7 integration detailed breakdown
- #1380: Performance validation
- #1381: Rollback plan
- #1382: Test fixtures infrastructure
- #1383: Edge case testing

### Task 2 Edge Cases (Add to Step 1)

```typescript
describe('getBestCardPosition edge cases', () => {
  it('handles card larger than available space', () => {
    const cardSize = { width: 1000, height: 800 };
    const viewport = { width: 800, height: 600 };
    const nodePos = { x: 400, y: 300 };

    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.position.x).toBeGreaterThanOrEqual(0);
    expect(result.position.x + cardSize.width).toBeLessThanOrEqual(viewport.width);
  });

  it('handles node at exact viewport edge', () => {
    const nodePos = { x: 0, y: 0 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.position.x).toBeGreaterThanOrEqual(0);
    expect(result.position.y).toBeGreaterThanOrEqual(0);
  });

  it('clamps position to viewport bounds', () => {
    const nodePos = { x: 1180, y: 780 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.position.x + cardSize.width).toBeLessThanOrEqual(viewport.width);
    expect(result.position.y + cardSize.height).toBeLessThanOrEqual(viewport.height);
  });
});
```

### Task 3 Mobile Constants (Add)

```typescript
export const MOBILE_BEHAVIOR = {
  cardPosition: 'bottom-fixed',
  sidebarType: 'overlay',
  graphDimOpacity: 0.4,
  swipeDismissThreshold: 50,
} as const;

export const PANEL_DIMENSIONS = {
  card: {
    width: 280,
    maxHeight: 400,
    margin: 20,
    mobileBottom: '20%',
  },
  sidebar: {
    widthPercent: 35,
    tabletWidthPercent: 50,
    mobileWidth: '100%',
    minWidth: 320,
    maxWidth: 500,
  },
} as const;
```

### Task 4 Test Fixtures (Create Before Tests)

Create `frontend/src/composables/socialcircles/__tests__/fixtures.ts`:

```typescript
import type { ApiNode, ApiEdge, NodeId, EdgeId } from '@/types/socialCircles';

export const mockAuthor1: ApiNode = {
  id: 'author:1' as NodeId,
  entity_id: 1,
  name: 'Charles Dickens',
  type: 'author',
  book_count: 12,
  book_ids: [1, 2, 3],
  birth_year: 1812,
  death_year: 1870,
};

export const mockPublisher1: ApiNode = {
  id: 'publisher:1' as NodeId,
  entity_id: 1,
  name: 'Chapman & Hall',
  type: 'publisher',
  tier: 'TIER_1',
  book_count: 8,
  book_ids: [1, 2],
};

export const mockBinder1: ApiNode = {
  id: 'binder:1' as NodeId,
  entity_id: 1,
  name: 'Rivière & Son',
  type: 'binder',
  tier: 'TIER_1',
  book_count: 6,
  book_ids: [1],
};

export const mockEdge1: ApiEdge = {
  id: 'e:author:1:publisher:1' as EdgeId,
  source: 'author:1' as NodeId,
  target: 'publisher:1' as NodeId,
  type: 'publisher',
  strength: 4,
  shared_book_ids: [1, 2],
};

export const mockNodes = [mockAuthor1, mockPublisher1, mockBinder1];
export const mockEdges = [mockEdge1];
```

### Task 5-6 Component Tests

Add to each component task after Step 2:

**NodeFloatingCard.test.ts**
```typescript
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import NodeFloatingCard from '../NodeFloatingCard.vue';
import { mockAuthor1 } from '@/composables/socialcircles/__tests__/fixtures';

describe('NodeFloatingCard', () => {
  it('renders author card with correct data', () => {
    const wrapper = mount(NodeFloatingCard, {
      props: {
        node: mockAuthor1,
        nodePosition: { x: 100, y: 100 },
        viewportSize: { width: 1200, height: 800 },
        edges: [],
        nodes: [],
        isOpen: true,
      },
    });
    expect(wrapper.text()).toContain('Charles Dickens');
  });

  it('emits close when X button clicked', async () => {
    const wrapper = mount(NodeFloatingCard, { /* props */ });
    await wrapper.find('.node-floating-card__close').trigger('click');
    expect(wrapper.emitted('close')).toBeTruthy();
  });

  it('does not render when isOpen is false', () => {
    const wrapper = mount(NodeFloatingCard, {
      props: { /* ... */ isOpen: false },
    });
    expect(wrapper.find('.node-floating-card').exists()).toBe(false);
  });
});
```

### Task 7 Detailed Integration Steps

**Step 2.1: Remove old imports**
```typescript
// DELETE:
import NodeDetailPanel from '@/components/socialcircles/NodeDetailPanel.vue';
// ADD:
import NodeFloatingCard from '@/components/socialcircles/NodeFloatingCard.vue';
import EdgeSidebar from '@/components/socialcircles/EdgeSidebar.vue';
```

**Step 2.2: Add viewport tracking**
```typescript
import { useWindowSize } from '@vueuse/core';
const { width: viewportWidth, height: viewportHeight } = useWindowSize();
const viewport = computed(() => ({
  width: viewportWidth.value,
  height: viewportHeight.value,
}));
```

**Step 2.3: Add node position getter**
```typescript
function getNodePosition(nodeId: NodeId): Position | null {
  if (!cy.value) return null;
  const node = cy.value.$id(nodeId);
  if (node.length === 0) return null;
  const renderedPos = node.renderedPosition();
  return { x: renderedPos.x, y: renderedPos.y };
}
```

**Step 2.4: Add Cytoscape click handlers**
```typescript
cy.value.on('tap', 'node', (event) => {
  const nodeId = event.target.id() as NodeId;
  socialCircles.toggleSelectNode(nodeId);
});

cy.value.on('tap', 'edge', (event) => {
  const edgeId = event.target.id() as EdgeId;
  socialCircles.toggleSelectEdge(edgeId);
});

cy.value.on('tap', (event) => {
  if (event.target === cy.value) {
    socialCircles.clearSelection();
  }
});
```

**Step 2.5: Add template**
```vue
<NodeFloatingCard
  v-if="socialCircles.isNodeSelected.value && socialCircles.isPanelOpen.value"
  :node="socialCircles.selectedNode.value!"
  :node-position="cardPosition"
  :viewport-size="viewport"
  :edges="socialCircles.edges.value"
  :nodes="socialCircles.nodes.value"
  :is-open="socialCircles.isPanelOpen.value"
  @close="socialCircles.closePanel"
  @select-edge="handleSelectEdge"
  @view-profile="handleViewProfile"
/>

<EdgeSidebar
  v-if="socialCircles.isEdgeSelected.value && socialCircles.isPanelOpen.value"
  :edge="socialCircles.selectedEdge.value!"
  :nodes="socialCircles.nodes.value"
  :is-open="socialCircles.isPanelOpen.value"
  @close="socialCircles.closePanel"
  @select-node="socialCircles.selectNode"
/>
```

### Task 10 Performance Validation (Add to Step 3)

**Performance checklist:**
- [ ] Card animation runs at 60fps (DevTools Performance tab)
- [ ] No layout thrashing (Rendering → Paint flashing)
- [ ] Smart positioning calculates in <16ms
- [ ] No memory leaks (open/close 20x, check heap)
- [ ] Placeholder images load <500ms on 3G
- [ ] Mobile touch targets 44x44px minimum

### Rollback Strategy

If integration causes breaking issues:

**Step 1: Revert to previous working state**
```bash
git log --oneline --graph
git revert HEAD~3..HEAD
```

**Step 2: Re-enable old NodeDetailPanel temporarily**
```bash
git checkout main -- frontend/src/components/socialcircles/NodeDetailPanel.vue
```

**Step 3: Fix issues in feature branch**
```bash
git checkout -b fix/node-panel-integration
```

**Step 4: Document regression**
- Open GitHub issue with reproduction steps
- Add to "Known Issues" in README

---

## Wave Progress

### Wave 1 (Foundation) - COMPLETE ✅
- [x] Task 0: Bug fix (commit: `4037e8f`)
- [x] Task 1: Formatters (commit: `af0f4d0`)
- [x] Task 2: Positioning (commit: `a46355c`)
- [x] Task 3: Constants (commit: `7a09ffc`)

### Wave 2 (State & Components) - PENDING
- [ ] Task 4: Selection state enhancement
- [ ] Task 5: NodeFloatingCard component
- [ ] Task 6: EdgeSidebar component

### Wave 3 (Integration & Polish) - PENDING
- [ ] Task 7: Integration with SocialCirclesView
- [ ] Task 8: Placeholder images
- [ ] Task 9: Remove old component
- [ ] Task 10: Final validation
