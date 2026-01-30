<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, shallowRef, watch } from "vue";
import cytoscape from "cytoscape";
import type { ProfileConnection } from "@/types/entityProfile";

const props = defineProps<{
  entityId: number;
  entityType: string;
  entityName: string;
  connections: ProfileConnection[];
}>();

const containerRef = ref<HTMLElement | null>(null);
const cy = shallowRef<cytoscape.Core | null>(null);

// Local element type avoids conflict with the Social Circles module augmentation
// in cytoscape.d.ts which narrows NodeDataDefinition to branded NodeId/EdgeId types.
interface EgoElement {
  data: Record<string, unknown>;
}

function buildElements(): EgoElement[] {
  const centerId = `${props.entityType}:${props.entityId}`;

  const nodes: EgoElement[] = [
    {
      data: {
        id: centerId,
        label: props.entityName,
        isCenter: true,
        type: props.entityType,
      },
    },
  ];

  const edges: EgoElement[] = [];

  for (const conn of props.connections) {
    const connId = `${conn.entity.type}:${conn.entity.id}`;
    nodes.push({
      data: {
        id: connId,
        label: conn.entity.name,
        isCenter: false,
        type: conn.entity.type,
        isKey: conn.is_key,
      },
    });
    edges.push({
      data: {
        id: `edge-${centerId}-${connId}`,
        source: centerId,
        target: connId,
        strength: conn.strength,
      },
    });
  }

  return [...nodes, ...edges];
}

function initCytoscape() {
  if (!containerRef.value) return;
  cy.value?.destroy();

  cy.value = cytoscape({
    container: containerRef.value,
    elements: buildElements() as cytoscape.ElementDefinition[],
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "text-valign": "bottom",
          "text-halign": "center",
          "font-size": "10px",
          "text-margin-y": 6,
          "background-color": "#8b8579",
          width: 24,
          height: 24,
          "text-max-width": "80px",
          "text-wrap": "ellipsis",
        },
      },
      {
        selector: "node[?isCenter]",
        style: {
          "background-color": "#b8860b",
          "border-width": 3,
          "border-color": "#8b6914",
          width: 40,
          height: 40,
          "font-size": "12px",
          "font-weight": "bold",
        },
      },
      {
        selector: "node[?isKey]",
        style: {
          "background-color": "#a0522d",
          width: 30,
          height: 30,
        },
      },
      {
        selector: "edge",
        style: {
          width: 1,
          "line-color": "#e8e4de",
          "curve-style": "bezier",
          opacity: 0.6,
        },
      },
    ],
    layout: {
      name: "concentric",
      concentric: (node: cytoscape.NodeSingular) => {
        return node.data("isCenter") ? 2 : 1;
      },
      levelWidth: () => 1,
      minNodeSpacing: 40,
      padding: 20,
      animate: false,
    },
    userZoomingEnabled: false,
    userPanningEnabled: false,
    boxSelectionEnabled: false,
  });
}

onMounted(initCytoscape);

watch(() => [props.entityId, props.connections], initCytoscape);

onBeforeUnmount(() => {
  cy.value?.destroy();
});
</script>

<template>
  <section v-if="connections.length > 0" class="ego-network">
    <h2 class="ego-network__title">Network</h2>
    <div ref="containerRef" class="ego-network__canvas" />
  </section>
</template>

<style scoped>
.ego-network__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.ego-network__canvas {
  width: 100%;
  height: 300px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  border: 1px solid var(--color-border, #e8e4de);
}
</style>
