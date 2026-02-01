import { describe, it, expect, vi, beforeEach } from "vitest";

const mockRouter = { push: vi.fn() };

vi.mock("vue-router", () => ({
  useRouter: () => mockRouter,
}));

// Mock cytoscape — jsdom has no layout engine so we simulate the API
let tapHandler: ((evt: { target: { data: (key: string) => unknown } }) => void) | null = null;

vi.mock("cytoscape", () => ({
  default: vi.fn(() => ({
    on: vi.fn(
      (
        event: string,
        _selectorOrHandler: string | ((...args: unknown[]) => void),
        handler?: (...args: unknown[]) => void
      ) => {
        if (event === "tap" && typeof handler === "function") {
          tapHandler = handler as typeof tapHandler;
        }
      }
    ),
    destroy: vi.fn(),
  })),
}));

import { mount } from "@vue/test-utils";
import EgoNetwork from "../EgoNetwork.vue";
import type { ProfileConnection } from "@/types/entityProfile";

const connections: ProfileConnection[] = [
  {
    entity: { id: 31, type: "author", name: "Elizabeth Barrett Browning" },
    connection_type: "literary_associate",
    strength: 8,
    shared_book_count: 3,
    shared_books: [],
    narrative: "Close associates.",
    narrative_trigger: null,
    is_key: true,
    relationship_story: null,
  },
];

describe("EgoNetwork", () => {
  beforeEach(() => {
    mockRouter.push.mockClear();
    tapHandler = null;
  });

  it("navigates to entity profile when a non-center node is tapped", () => {
    mount(EgoNetwork, {
      props: {
        entityId: 10,
        entityType: "author",
        entityName: "Robert Browning",
        connections,
      },
      attachTo: document.createElement("div"),
    });

    expect(tapHandler).not.toBeNull();

    // Simulate tapping a connected node (not the center)
    tapHandler!({
      target: {
        data: (key: string) => {
          const nodeData: Record<string, unknown> = {
            entityType: "author",
            entityId: 31,
          };
          return nodeData[key];
        },
      },
    });

    expect(mockRouter.push).toHaveBeenCalledWith({
      name: "entity-profile",
      params: { type: "author", id: "31" },
    });
  });

  it("does not navigate when the center node is tapped", () => {
    mount(EgoNetwork, {
      props: {
        entityId: 10,
        entityType: "author",
        entityName: "Robert Browning",
        connections,
      },
      attachTo: document.createElement("div"),
    });

    expect(tapHandler).not.toBeNull();

    // Simulate tapping the center node (entityId matches props.entityId)
    tapHandler!({
      target: {
        data: (key: string) => {
          const nodeData: Record<string, unknown> = {
            entityType: "author",
            entityId: 10,
          };
          return nodeData[key];
        },
      },
    });

    expect(mockRouter.push).not.toHaveBeenCalled();
  });
});
