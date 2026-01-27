/**
 * Transform API data to Cytoscape format.
 */

import type { Core, ElementDefinition } from "cytoscape";
import type {
  ApiNode,
  ApiEdge,
  SocialCirclesResponse,
  NodeType,
  ConnectionType,
} from "@/types/socialCircles";
import {
  NODE_COLORS,
  NODE_SHAPES,
  EDGE_COLORS,
  EDGE_STYLES,
  calculateNodeSize,
  calculateEdgeWidth,
} from "@/constants/socialCircles";

function getNodeColorKey(node: ApiNode): string {
  const { type, era, tier } = node;
  if (type === "author" && era) return `author:${era}`;
  if (type === "publisher" && tier) {
    const tierKey = tier === "TIER_1" ? "tier1" : "tier2";
    return `publisher:${tierKey}`;
  }
  if (type === "binder" && tier === "TIER_1") return "binder:tier1";
  return `${type}:default`;
}

export function transformNode(node: ApiNode): ElementDefinition {
  const colorKey = getNodeColorKey(node);
  const color = NODE_COLORS[colorKey] || NODE_COLORS[`${node.type}:default`];
  const shape = NODE_SHAPES[node.type];
  const size = calculateNodeSize(node.type, node.book_count);

  // Flatten style properties - Cytoscape data() doesn't support nested paths
  return {
    group: "nodes",
    data: {
      ...node,
      nodeColor: color,
      nodeShape: shape,
      nodeSize: size,
    },
  };
}

export function transformEdge(edge: ApiEdge): ElementDefinition {
  const color = EDGE_COLORS[edge.type];
  const { lineStyle, opacity } = EDGE_STYLES[edge.type];
  const width = calculateEdgeWidth(edge.strength);

  // Flatten style properties - Cytoscape data() doesn't support nested paths
  return {
    group: "edges",
    data: {
      ...edge,
      edgeColor: color,
      edgeStyle: lineStyle,
      edgeOpacity: opacity,
      edgeWidth: width,
    },
  };
}

export function transformToCytoscapeElements(response: SocialCirclesResponse): ElementDefinition[] {
  const nodeElements = response.nodes.map(transformNode);
  const edgeElements = response.edges.map(transformEdge);
  return [...nodeElements, ...edgeElements];
}

export function getVisibleElementIds(
  cy: Core,
  showAuthors: boolean,
  showPublishers: boolean,
  showBinders: boolean,
  connectionTypes: ConnectionType[]
): { nodeIds: Set<string>; edgeIds: Set<string> } {
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();

  cy.nodes().forEach((node) => {
    const nodeType = node.data("type") as NodeType;
    if (nodeType === "author" && showAuthors) nodeIds.add(node.id());
    else if (nodeType === "publisher" && showPublishers) nodeIds.add(node.id());
    else if (nodeType === "binder" && showBinders) nodeIds.add(node.id());
  });

  cy.edges().forEach((edge) => {
    const edgeType = edge.data("type") as ConnectionType;
    const sourceId = edge.source().id();
    const targetId = edge.target().id();
    if (connectionTypes.includes(edgeType) && nodeIds.has(sourceId) && nodeIds.has(targetId)) {
      edgeIds.add(edge.id());
    }
  });

  return { nodeIds, edgeIds };
}
