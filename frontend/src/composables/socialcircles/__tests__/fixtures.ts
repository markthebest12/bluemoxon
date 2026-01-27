import type { ApiNode, ApiEdge, NodeId, EdgeId, BookId } from "@/types/socialCircles";

export const mockAuthor1: ApiNode = {
  id: "author:1" as NodeId,
  entity_id: 1,
  name: "Charles Dickens",
  type: "author",
  book_count: 12,
  book_ids: [1 as BookId, 2 as BookId, 3 as BookId],
  birth_year: 1812,
  death_year: 1870,
};

export const mockPublisher1: ApiNode = {
  id: "publisher:1" as NodeId,
  entity_id: 1,
  name: "Chapman & Hall",
  type: "publisher",
  tier: "TIER_1",
  book_count: 8,
  book_ids: [1 as BookId, 2 as BookId],
};

export const mockBinder1: ApiNode = {
  id: "binder:1" as NodeId,
  entity_id: 1,
  name: "Riviere & Son",
  type: "binder",
  tier: "TIER_1",
  book_count: 6,
  book_ids: [1 as BookId],
};

export const mockEdge1: ApiEdge = {
  id: "e:author:1:publisher:1" as EdgeId,
  source: "author:1" as NodeId,
  target: "publisher:1" as NodeId,
  type: "publisher",
  strength: 4,
  shared_book_ids: [1 as BookId, 2 as BookId],
};

export const mockNodes = [mockAuthor1, mockPublisher1, mockBinder1];
export const mockEdges = [mockEdge1];
