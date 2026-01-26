// frontend/src/types/cytoscape.d.ts

/**
 * Cytoscape.js type extensions for Social Circles.
 * Extends core Cytoscape types with our custom data shapes.
 */

import type { NodeId, EdgeId, NodeType, ConnectionType, Era, Tier, BookId } from "./socialCircles";

declare module "cytoscape" {
  interface NodeDataDefinition {
    id: NodeId;
    entity_id: number;
    name: string;
    type: NodeType;
    birth_year?: number;
    death_year?: number;
    era?: Era;
    tier?: Tier;
    founded_year?: number;
    closed_year?: number;
    book_count: number;
    book_ids: BookId[];
  }

  interface EdgeDataDefinition {
    id: EdgeId;
    source: NodeId;
    target: NodeId;
    type: ConnectionType;
    strength: number;
    evidence?: string;
    shared_book_ids?: BookId[];
    start_year?: number;
    end_year?: number;
  }
}

export {};
