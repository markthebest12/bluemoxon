import { describe, it, expect, vi, beforeEach } from "vitest";

const mockRouter = { push: vi.fn() };

vi.mock("vue-router", () => ({
  useRouter: () => mockRouter,
}));

// Mock cytoscape — jsdom has no layout engine so we simulate the API.
// Each test captures its own tapHandler via the shared mock.
const tapHandlers: Array<(evt: { target: { data: (key: string) => unknown } }) => void> = [];

vi.mock("cytoscape", () => ({
  default: vi.fn(() => ({
    on: vi.fn(
      (
        event: string,
        _selectorOrHandler: string | ((...args: unknown[]) => void),
        handler?: (...args: unknown[]) => void
      ) => {
        if (event === "tap" && typeof handler === "function") {
          tapHandlers.push(
            handler as (evt: { target: { data: (key: string) => unknown } }) => void
          );
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
    entity: { id: 31, type: "author", name: "Elizabeth Barrett Browning", image_url: null },
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

function lastTapHandler() {
  return tapHandlers[tapHandlers.length - 1] ?? null;
}

function simulateTap(data: Record<string, unknown>) {
  const handler = lastTapHandler();
  expect(handler).not.toBeNull();
  handler!({
    target: {
      data: (key: string) => data[key],
    },
  });
}

describe("EgoNetwork", () => {
  beforeEach(() => {
    mockRouter.push.mockClear();
    tapHandlers.length = 0;
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

    simulateTap({ entityType: "author", entityId: 31 });

    expect(mockRouter.push).toHaveBeenCalledWith({
      name: "entity-profile",
      params: { type: "author", id: "31" },
    });
  });

  it("does not navigate when the center node is tapped", () => {
    // Center node has no entityType/entityId in its data (see EgoNetwork.vue buildElements).
    // The tap handler short-circuits on `entityType &&` being undefined.
    mount(EgoNetwork, {
      props: {
        entityId: 10,
        entityType: "author",
        entityName: "Robert Browning",
        connections,
      },
      attachTo: document.createElement("div"),
    });

    simulateTap({ isCenter: true, type: "author" });

    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  it("does not navigate when tapped node has same entityId as center", () => {
    // Tests the `entityId !== props.entityId` guard for a non-center node
    // that happens to share the same ID as the center entity.
    mount(EgoNetwork, {
      props: {
        entityId: 10,
        entityType: "author",
        entityName: "Robert Browning",
        connections,
      },
      attachTo: document.createElement("div"),
    });

    simulateTap({ entityType: "author", entityId: 10 });

    expect(mockRouter.push).not.toHaveBeenCalled();
  });
});
