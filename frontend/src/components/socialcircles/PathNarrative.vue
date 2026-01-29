<!-- frontend/src/components/socialcircles/PathNarrative.vue -->
<script setup lang="ts">
/**
 * PathNarrative - Human-readable narrative of a path between people.
 * Displays the connection chain with clickable nodes and a summary sentence.
 */

import { computed } from "vue";
import type { ApiNode, ApiEdge, NodeType, ConnectionType } from "@/types/socialCircles";

interface Props {
  path: string[];
  nodes: ApiNode[];
  edges: ApiEdge[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "select-node", nodeId: string): void;
}>();

/** Display labels for entity types */
const TYPE_LABELS: Record<NodeType, string> = {
  author: "author",
  publisher: "publisher",
  binder: "bindery",
};

/** Display labels for connection types */
const CONNECTION_LABELS: Record<ConnectionType, string> = {
  publisher: "published by",
  shared_publisher: "shared publisher with",
  binder: "bound by",
};

/** Node lookup map for efficient access */
const nodeMap = computed(() => {
  const map = new Map<string, ApiNode>();
  props.nodes.forEach((node) => {
    map.set(node.id, node);
  });
  return map;
});

/** Edge lookup by source-target pair */
const edgeMap = computed(() => {
  const map = new Map<string, ApiEdge>();
  props.edges.forEach((edge) => {
    // Store both directions for undirected lookup
    map.set(`${edge.source}:${edge.target}`, edge);
    map.set(`${edge.target}:${edge.source}`, edge);
  });
  return map;
});

/** Computed path steps with node details */
interface PathStep {
  nodeId: string;
  node: ApiNode | null;
  edgeToNext: ApiEdge | null;
}

const pathSteps = computed((): PathStep[] => {
  return props.path.map((nodeId, index) => {
    const node = nodeMap.value.get(nodeId) || null;
    let edgeToNext: ApiEdge | null = null;

    if (index < props.path.length - 1) {
      const nextNodeId = props.path[index + 1];
      edgeToNext = edgeMap.value.get(`${nodeId}:${nextNodeId}`) || null;
    }

    return { nodeId, node, edgeToNext };
  });
});

/** Start and end nodes for the summary */
const startNode = computed(() => {
  if (props.path.length === 0) return null;
  return nodeMap.value.get(props.path[0]) || null;
});

const endNode = computed(() => {
  if (props.path.length < 2) return null;
  return nodeMap.value.get(props.path[props.path.length - 1]) || null;
});

/** Degrees of separation */
const degrees = computed(() => {
  return Math.max(0, props.path.length - 1);
});

/** Intermediary name for summary (if exactly one hop) */
const intermediaryName = computed(() => {
  if (props.path.length !== 3) return null;
  const middleNode = nodeMap.value.get(props.path[1]);
  return middleNode?.name || null;
});

/** Get type label for a node */
function getTypeLabel(node: ApiNode | null): string {
  if (!node) return "";
  return TYPE_LABELS[node.type] || node.type;
}

/** Get connection description between nodes */
function getConnectionDescription(edge: ApiEdge | null): string {
  if (!edge) return "";
  return CONNECTION_LABELS[edge.type] || edge.type.replace("_", " ");
}

/** Handle node click */
function handleNodeClick(nodeId: string) {
  emit("select-node", nodeId);
}
</script>

<template>
  <div v-if="path.length >= 2" class="path-narrative" data-testid="path-narrative">
    <!-- Path chain visualization -->
    <div class="path-narrative__chain" data-testid="path-narrative-chain">
      <template v-for="(step, index) in pathSteps" :key="step.nodeId">
        <!-- Node -->
        <button
          class="path-narrative__node"
          :class="`path-narrative__node--${step.node?.type || 'unknown'}`"
          data-testid="path-narrative-node"
          @click="handleNodeClick(step.nodeId)"
        >
          <span class="path-narrative__node-name">{{ step.node?.name || "Unknown" }}</span>
          <span class="path-narrative__node-type">({{ getTypeLabel(step.node) }})</span>
        </button>

        <!-- Arrow with connection info -->
        <span v-if="index < pathSteps.length - 1" class="path-narrative__arrow">
          <span class="path-narrative__arrow-symbol">&rarr;</span>
          <span v-if="step.edgeToNext" class="path-narrative__connection-label">
            {{ getConnectionDescription(step.edgeToNext) }}
          </span>
        </span>
      </template>
    </div>

    <!-- Summary sentence -->
    <p class="path-narrative__summary" data-testid="path-narrative-summary">
      <template v-if="startNode && endNode">
        <span class="path-narrative__summary-highlight">{{ startNode.name }}</span>
        is
        <span class="path-narrative__summary-degrees">{{ degrees }}</span>
        {{ degrees === 1 ? "degree" : "degrees" }} from
        <span class="path-narrative__summary-highlight">{{ endNode.name }}</span>
        <template v-if="intermediaryName">
          via
          <span class="path-narrative__summary-via">{{ intermediaryName }}</span>
        </template>
      </template>
    </p>
  </div>

  <!-- Empty state -->
  <div v-else-if="path.length === 1" class="path-narrative path-narrative--single">
    <p class="path-narrative__empty">
      <button class="path-narrative__node-inline" @click="handleNodeClick(path[0])">
        {{ nodeMap.get(path[0])?.name || "Selected node" }}
      </button>
      is the starting point. Select another node to find the path.
    </p>
  </div>

  <div v-else class="path-narrative path-narrative--empty">
    <p class="path-narrative__empty">Select two nodes to see the path between them.</p>
  </div>
</template>

<style scoped>
.path-narrative {
  font-family: Georgia, "Times New Roman", serif;
  padding: 16px;
  background: var(--color-card-bg, #f5f1e8);
  border: 1px solid var(--color-border, #d4cfc4);
  border-radius: 8px;
}

.path-narrative__chain {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.path-narrative__node {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 12px;
  background: white;
  border: 1px solid var(--color-border, #d4cfc4);
  border-radius: 4px;
  cursor: pointer;
  transition:
    background 150ms ease-out,
    border-color 150ms ease-out,
    transform 150ms ease-out;
}

.path-narrative__node:hover {
  background: rgba(184, 134, 11, 0.1);
  border-color: var(--color-accent-gold, #b8860b);
  transform: translateY(-2px);
}

.path-narrative__node:focus {
  outline: 2px solid var(--color-accent-gold, #b8860b);
  outline-offset: 2px;
}

.path-narrative__node--author {
  border-top: 3px solid var(--color-author, #7b4b94);
}

.path-narrative__node--publisher {
  border-top: 3px solid var(--color-publisher, #2c5f77);
}

.path-narrative__node--binder {
  border-top: 3px solid var(--color-binder, #8b4513);
}

.path-narrative__node--unknown {
  border-top: 3px solid var(--color-text-muted, #8b8579);
}

.path-narrative__node-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-primary, #2c2416);
  text-align: center;
}

.path-narrative__node-type {
  font-size: 0.75rem;
  font-style: italic;
  color: var(--color-text-muted, #8b8579);
}

.path-narrative__arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 0 4px;
}

.path-narrative__arrow-symbol {
  font-size: 1.25rem;
  color: var(--color-accent-gold, #b8860b);
}

.path-narrative__connection-label {
  font-size: 0.6875rem;
  font-style: italic;
  color: var(--color-text-muted, #8b8579);
  text-align: center;
  max-width: 80px;
  line-height: 1.2;
}

.path-narrative__summary {
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--color-text-secondary, #5c5446);
  margin: 0;
  padding-top: 12px;
  border-top: 1px solid var(--color-border, #d4cfc4);
  font-style: italic;
}

.path-narrative__summary-highlight {
  font-weight: 600;
  color: var(--color-text-primary, #2c2416);
  font-style: normal;
}

.path-narrative__summary-degrees {
  font-weight: 700;
  color: var(--color-accent-gold, #b8860b);
  font-style: normal;
}

.path-narrative__summary-via {
  font-weight: 600;
  color: var(--color-text-primary, #2c2416);
  font-style: normal;
}

.path-narrative--single,
.path-narrative--empty {
  text-align: center;
}

.path-narrative__empty {
  font-size: 0.875rem;
  color: var(--color-text-muted, #8b8579);
  margin: 0;
  font-style: italic;
}

.path-narrative__node-inline {
  background: none;
  border: none;
  font-family: inherit;
  font-size: inherit;
  font-weight: 600;
  color: var(--color-link, #6b4423);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-style: dotted;
  padding: 0;
}

.path-narrative__node-inline:hover {
  color: var(--color-accent-gold, #b8860b);
  text-decoration-style: solid;
}

/* Responsive: stack vertically on narrow screens */
@media (max-width: 480px) {
  .path-narrative__chain {
    flex-direction: column;
    align-items: stretch;
  }

  .path-narrative__node {
    flex-direction: row;
    justify-content: space-between;
    width: 100%;
  }

  .path-narrative__arrow {
    flex-direction: row;
    padding: 8px 0;
  }

  .path-narrative__arrow-symbol {
    transform: rotate(90deg);
  }

  .path-narrative__connection-label {
    max-width: none;
    margin-left: 8px;
  }
}
</style>
