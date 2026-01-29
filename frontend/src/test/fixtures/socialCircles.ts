/**
 * Social Circles test fixtures.
 *
 * Provides consistent mock data for testing Social Circles components and composables.
 * These fixtures mirror the API response structure for realistic testing.
 */

import type {
  ApiNode,
  ApiEdge,
  NodeId,
  EdgeId,
  BookId,
  SocialCirclesMeta,
  SocialCirclesResponse,
  NodeType,
  ConnectionType,
  Era,
  Tier,
} from "@/types/socialCircles";

// =============================================================================
// Author Fixtures
// =============================================================================

export const mockAuthor1: ApiNode = {
  id: "author:1" as NodeId,
  entity_id: 1,
  name: "Charles Dickens",
  type: "author" as NodeType,
  birth_year: 1812,
  death_year: 1870,
  era: "victorian" as Era,
  tier: "TIER_1" as Tier,
  book_count: 15,
  book_ids: [1, 2, 3, 4, 5] as BookId[],
};

export const mockAuthor2: ApiNode = {
  id: "author:2" as NodeId,
  entity_id: 2,
  name: "William Thackeray",
  type: "author" as NodeType,
  birth_year: 1811,
  death_year: 1863,
  era: "victorian" as Era,
  tier: "TIER_2" as Tier,
  book_count: 8,
  book_ids: [6, 7, 8] as BookId[],
};

export const mockAuthor3: ApiNode = {
  id: "author:3" as NodeId,
  entity_id: 3,
  name: "George Eliot",
  type: "author" as NodeType,
  birth_year: 1819,
  death_year: 1880,
  era: "victorian" as Era,
  tier: "TIER_1" as Tier,
  book_count: 10,
  book_ids: [9, 10] as BookId[],
};

export const mockAuthorRomantic: ApiNode = {
  id: "author:4" as NodeId,
  entity_id: 4,
  name: "Lord Byron",
  type: "author" as NodeType,
  birth_year: 1788,
  death_year: 1824,
  era: "romantic" as Era,
  tier: "TIER_1" as Tier,
  book_count: 6,
  book_ids: [11, 12] as BookId[],
};

export const mockAuthorEdwardian: ApiNode = {
  id: "author:5" as NodeId,
  entity_id: 5,
  name: "H.G. Wells",
  type: "author" as NodeType,
  birth_year: 1866,
  death_year: 1946,
  era: "edwardian" as Era,
  tier: "TIER_2" as Tier,
  book_count: 4,
  book_ids: [13, 14] as BookId[],
};

// =============================================================================
// Publisher Fixtures
// =============================================================================

export const mockPublisher1: ApiNode = {
  id: "publisher:1" as NodeId,
  entity_id: 1,
  name: "Chapman & Hall",
  type: "publisher" as NodeType,
  tier: "TIER_1" as Tier,
  book_count: 20,
  book_ids: [1, 2, 6] as BookId[],
};

export const mockPublisher2: ApiNode = {
  id: "publisher:2" as NodeId,
  entity_id: 2,
  name: "Bradbury & Evans",
  type: "publisher" as NodeType,
  tier: "TIER_2" as Tier,
  book_count: 12,
  book_ids: [3, 4, 7] as BookId[],
};

export const mockPublisher3: ApiNode = {
  id: "publisher:3" as NodeId,
  entity_id: 3,
  name: "John Murray",
  type: "publisher" as NodeType,
  tier: "TIER_1" as Tier,
  book_count: 15,
  book_ids: [11, 12] as BookId[],
};

// =============================================================================
// Binder Fixtures
// =============================================================================

export const mockBinder1: ApiNode = {
  id: "binder:1" as NodeId,
  entity_id: 1,
  name: "Riviere & Son",
  type: "binder" as NodeType,
  tier: "TIER_1" as Tier,
  book_count: 8,
  book_ids: [1, 6, 9] as BookId[],
};

export const mockBinder2: ApiNode = {
  id: "binder:2" as NodeId,
  entity_id: 2,
  name: "Zaehnsdorf",
  type: "binder" as NodeType,
  tier: "TIER_1" as Tier,
  book_count: 5,
  book_ids: [2, 7] as BookId[],
};

export const mockBinder3: ApiNode = {
  id: "binder:3" as NodeId,
  entity_id: 3,
  name: "Sangorski & Sutcliffe",
  type: "binder" as NodeType,
  tier: "TIER_2" as Tier,
  book_count: 3,
  book_ids: [11] as BookId[],
};

// =============================================================================
// Edge Fixtures
// =============================================================================

export const mockEdgeAuthorPublisher1: ApiEdge = {
  id: "e:author:1:publisher:1" as EdgeId,
  source: "author:1" as NodeId,
  target: "publisher:1" as NodeId,
  type: "publisher" as ConnectionType,
  strength: 8,
  evidence: "Published 5 works",
  shared_book_ids: [1, 2] as BookId[],
};

export const mockEdgeAuthorPublisher2: ApiEdge = {
  id: "e:author:1:publisher:2" as EdgeId,
  source: "author:1" as NodeId,
  target: "publisher:2" as NodeId,
  type: "publisher" as ConnectionType,
  strength: 6,
  evidence: "Published 3 works",
  shared_book_ids: [3, 4] as BookId[],
};

export const mockEdgeAuthorBinder: ApiEdge = {
  id: "e:author:1:binder:1" as EdgeId,
  source: "author:1" as NodeId,
  target: "binder:1" as NodeId,
  type: "binder" as ConnectionType,
  strength: 4,
  evidence: "Bound 2 works",
  shared_book_ids: [1] as BookId[],
};

export const mockEdgeSharedPublisher: ApiEdge = {
  id: "e:author:1:author:2" as EdgeId,
  source: "author:1" as NodeId,
  target: "author:2" as NodeId,
  type: "shared_publisher" as ConnectionType,
  strength: 3,
  evidence: "Both published by Chapman & Hall",
};

export const mockEdgeSharedPublisher2: ApiEdge = {
  id: "e:author:2:author:3" as EdgeId,
  source: "author:2" as NodeId,
  target: "author:3" as NodeId,
  type: "shared_publisher" as ConnectionType,
  strength: 2,
  evidence: "Both published by Bradbury & Evans",
};

// =============================================================================
// Aggregated Collections
// =============================================================================

/** All author nodes */
export const mockAuthors: ApiNode[] = [
  mockAuthor1,
  mockAuthor2,
  mockAuthor3,
  mockAuthorRomantic,
  mockAuthorEdwardian,
];

/** All publisher nodes */
export const mockPublishers: ApiNode[] = [mockPublisher1, mockPublisher2, mockPublisher3];

/** All binder nodes */
export const mockBinders: ApiNode[] = [mockBinder1, mockBinder2, mockBinder3];

/** All nodes combined */
export const mockNodes: ApiNode[] = [...mockAuthors, ...mockPublishers, ...mockBinders];

/** All edges */
export const mockEdges: ApiEdge[] = [
  mockEdgeAuthorPublisher1,
  mockEdgeAuthorPublisher2,
  mockEdgeAuthorBinder,
  mockEdgeSharedPublisher,
  mockEdgeSharedPublisher2,
];

// =============================================================================
// Response Fixtures
// =============================================================================

export const mockMeta: SocialCirclesMeta = {
  total_books: 100,
  total_authors: 5,
  total_publishers: 3,
  total_binders: 3,
  date_range: [1788, 1946],
  generated_at: "2026-01-27T12:00:00Z",
  truncated: false,
};

export const mockMetaTruncated: SocialCirclesMeta = {
  ...mockMeta,
  total_books: 5000,
  truncated: true,
};

export const mockResponse: SocialCirclesResponse = {
  nodes: mockNodes,
  edges: mockEdges,
  meta: mockMeta,
};

export const mockResponseTruncated: SocialCirclesResponse = {
  nodes: mockNodes,
  edges: mockEdges,
  meta: mockMetaTruncated,
};

export const mockResponseEmpty: SocialCirclesResponse = {
  nodes: [],
  edges: [],
  meta: {
    total_books: 0,
    total_authors: 0,
    total_publishers: 0,
    total_binders: 0,
    date_range: [1800, 1900],
    generated_at: "2026-01-27T12:00:00Z",
    truncated: false,
  },
};

// =============================================================================
// Factory Functions
// =============================================================================

/** Create a custom author node with overrides */
export function createMockAuthor(overrides: Partial<ApiNode> = {}): ApiNode {
  return {
    id: `author:${Date.now()}` as NodeId,
    entity_id: Date.now(),
    name: "Test Author",
    type: "author" as NodeType,
    birth_year: 1850,
    death_year: 1920,
    era: "victorian" as Era,
    tier: "TIER_2" as Tier,
    book_count: 5,
    book_ids: [1, 2, 3] as BookId[],
    ...overrides,
  };
}

/** Create a custom publisher node with overrides */
export function createMockPublisher(overrides: Partial<ApiNode> = {}): ApiNode {
  return {
    id: `publisher:${Date.now()}` as NodeId,
    entity_id: Date.now(),
    name: "Test Publisher",
    type: "publisher" as NodeType,
    tier: "TIER_2" as Tier,
    book_count: 10,
    book_ids: [1, 2] as BookId[],
    ...overrides,
  };
}

/** Create a custom binder node with overrides */
export function createMockBinder(overrides: Partial<ApiNode> = {}): ApiNode {
  return {
    id: `binder:${Date.now()}` as NodeId,
    entity_id: Date.now(),
    name: "Test Binder",
    type: "binder" as NodeType,
    tier: "TIER_2" as Tier,
    book_count: 3,
    book_ids: [1] as BookId[],
    ...overrides,
  };
}

/** Create a custom edge with overrides */
export function createMockEdge(
  source: NodeId,
  target: NodeId,
  type: ConnectionType = "publisher",
  overrides: Partial<ApiEdge> = {}
): ApiEdge {
  return {
    id: `e:${source}:${target}` as EdgeId,
    source,
    target,
    type,
    strength: 5,
    evidence: `Connection via ${type}`,
    shared_book_ids: [1, 2] as BookId[],
    ...overrides,
  };
}

/** Create a complete mock response with custom data */
export function createMockResponse(
  nodes: ApiNode[] = mockNodes,
  edges: ApiEdge[] = mockEdges,
  metaOverrides: Partial<SocialCirclesMeta> = {}
): SocialCirclesResponse {
  return {
    nodes,
    edges,
    meta: {
      total_books: nodes.reduce((sum, n) => sum + n.book_count, 0),
      total_authors: nodes.filter((n) => n.type === "author").length,
      total_publishers: nodes.filter((n) => n.type === "publisher").length,
      total_binders: nodes.filter((n) => n.type === "binder").length,
      date_range: [1800, 1900],
      generated_at: new Date().toISOString(),
      truncated: false,
      ...metaOverrides,
    },
  };
}
