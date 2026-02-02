import type { ProfileConnection } from "@/types/entityProfile";

/**
 * Shared cross-link test fixtures for entity profile component tests.
 * Used by EntityLinkedText, ProfileHero, and ConnectionGossipPanel tests.
 */
export const mockCrossLinkConnections: ProfileConnection[] = [
  {
    entity: { id: 32, type: "author", name: "Robert Browning" },
    connection_type: "shared_publisher",
    strength: 5,
    shared_book_count: 2,
    shared_books: [],
    narrative: null,
    narrative_trigger: null,
    is_key: true,
    relationship_story: null,
  },
  {
    entity: { id: 7, type: "publisher", name: "Smith, Elder & Co." },
    connection_type: "publisher",
    strength: 3,
    shared_book_count: 4,
    shared_books: [],
    narrative: null,
    narrative_trigger: null,
    is_key: false,
    relationship_story: null,
  },
];
