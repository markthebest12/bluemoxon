// frontend/src/types/socialCircles.ts

/**
 * Social Circles domain types.
 * Uses branded types for type-safe IDs.
 */

// =============================================================================
// Branded ID Types
// =============================================================================

/** Node identifier (e.g., "author:42", "publisher:7") */
export type NodeId = string & { readonly __brand: "NodeId" };

/** Edge identifier (e.g., "e:author:42:publisher:7") */
export type EdgeId = string & { readonly __brand: "EdgeId" };

/** Book ID reference */
export type BookId = number & { readonly __brand: "BookId" };

// =============================================================================
// Enums
// =============================================================================

export type NodeType = "author" | "publisher" | "binder";

export type ConnectionType = "publisher" | "shared_publisher" | "binder";

export type Era = "pre_romantic" | "romantic" | "victorian" | "edwardian" | "post_1910" | "unknown";

export type Tier = "Tier 1" | "Tier 2" | "Tier 3" | null;

export type LoadingState = "idle" | "loading" | "success" | "error";

export type LayoutMode = "force" | "circle" | "grid" | "hierarchical";

export type TimelineMode = "point" | "range";

export type PlaybackSpeed = 0.5 | 1 | 2 | 5;

// =============================================================================
// API Response Types
// =============================================================================

export interface ApiNode {
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

export interface ApiEdge {
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

export interface SocialCirclesMeta {
  total_books: number;
  total_authors: number;
  total_publishers: number;
  total_binders: number;
  date_range: [number, number];
  generated_at: string;
}

export interface SocialCirclesResponse {
  nodes: ApiNode[];
  edges: ApiEdge[];
  meta: SocialCirclesMeta;
}

// =============================================================================
// State Types
// =============================================================================

export interface FilterState {
  showAuthors: boolean;
  showPublishers: boolean;
  showBinders: boolean;
  connectionTypes: ConnectionType[];
  tier1Only: boolean;
  eras: Era[];
  searchQuery: string;
}

export interface TimelineState {
  currentYear: number;
  minYear: number;
  maxYear: number;
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;
  mode: TimelineMode;
  rangeStart?: number;
  rangeEnd?: number;
}

export interface SelectionState {
  selectedNodeId: NodeId | null;
  selectedEdgeId: EdgeId | null;
  highlightedNodeIds: Set<NodeId>;
  highlightedEdgeIds: Set<EdgeId>;
  hoveredNodeId: NodeId | null;
  hoveredEdgeId: EdgeId | null;
}

// =============================================================================
// Error Types
// =============================================================================

export type ErrorType = "network" | "parse" | "not_found" | "timeout" | "unknown";

export interface AppError {
  type: ErrorType;
  message: string;
  retryable: boolean;
}

export type Result<T, E = AppError> = { success: true; data: T } | { success: false; error: E };

// =============================================================================
// Type Guards & Validators
// =============================================================================

const NODE_ID_PATTERN = /^(author|publisher|binder):\d+$/;
const EDGE_ID_PATTERN = /^e:(author|publisher|binder):\d+:(author|publisher|binder):\d+$/;

export function isNodeId(id: string): id is NodeId {
  return NODE_ID_PATTERN.test(id);
}

export function isEdgeId(id: string): id is EdgeId {
  return EDGE_ID_PATTERN.test(id);
}

export function createNodeId(type: NodeType, entityId: number): NodeId {
  return `${type}:${entityId}` as NodeId;
}

export function createEdgeId(source: NodeId, target: NodeId): EdgeId {
  return `e:${source}:${target}` as EdgeId;
}

export function parseNodeId(id: NodeId): { type: NodeType; entityId: number } {
  const [type, entityId] = id.split(":");
  return { type: type as NodeType, entityId: parseInt(entityId, 10) };
}

// Node type guards
export function isAuthorNode(node: ApiNode): node is ApiNode & { type: "author" } {
  return node.type === "author";
}

export function isPublisherNode(node: ApiNode): node is ApiNode & { type: "publisher" } {
  return node.type === "publisher";
}

export function isBinderNode(node: ApiNode): node is ApiNode & { type: "binder" } {
  return node.type === "binder";
}

// =============================================================================
// Default Values
// =============================================================================

export const DEFAULT_FILTER_STATE: FilterState = {
  showAuthors: true,
  showPublishers: true,
  showBinders: true,
  connectionTypes: ["publisher", "shared_publisher", "binder"],
  tier1Only: false,
  eras: [],
  searchQuery: "",
};

export const DEFAULT_TIMELINE_STATE: TimelineState = {
  currentYear: 1850,
  minYear: 1780,
  maxYear: 1920,
  isPlaying: false,
  playbackSpeed: 1,
  mode: "point",
  rangeStart: undefined,
  rangeEnd: undefined,
};

export const DEFAULT_SELECTION_STATE: SelectionState = {
  selectedNodeId: null,
  selectedEdgeId: null,
  highlightedNodeIds: new Set(),
  highlightedEdgeIds: new Set(),
  hoveredNodeId: null,
  hoveredEdgeId: null,
};
