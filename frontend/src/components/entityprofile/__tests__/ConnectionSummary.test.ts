import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import ConnectionSummary from "../ConnectionSummary.vue";
import type { ProfileConnection } from "@/types/entityProfile";

let nextId = 1;
function makeConn(name: string, isKey: boolean): ProfileConnection {
  return {
    entity: { id: nextId++, type: "author", name },
    connection_type: "associate",
    strength: 5,
    shared_book_count: 1,
    shared_books: [],
    narrative: null,
    narrative_trigger: null,
    is_key: isKey,
    relationship_story: null,
  };
}

describe("ConnectionSummary", () => {
  beforeEach(() => {
    nextId = 1;
  });
  it("renders total connection count", () => {
    const conns = [makeConn("Alice", true), makeConn("Bob", true), makeConn("Carol", false)];
    const wrapper = mount(ConnectionSummary, { props: { connections: conns } });
    expect(wrapper.text()).toContain("3");
  });

  it("lists key connection names", () => {
    const conns = [makeConn("Dickens", true), makeConn("Morris", true), makeConn("Other", false)];
    const wrapper = mount(ConnectionSummary, { props: { connections: conns } });
    expect(wrapper.text()).toContain("Dickens");
    expect(wrapper.text()).toContain("Morris");
  });

  it("limits displayed names to 3", () => {
    const conns = [
      makeConn("A", true),
      makeConn("B", true),
      makeConn("C", true),
      makeConn("D", true),
      makeConn("E", false),
    ];
    const wrapper = mount(ConnectionSummary, { props: { connections: conns } });
    expect(wrapper.text()).toContain("and 2 others");
  });

  it("renders nothing when no connections", () => {
    const wrapper = mount(ConnectionSummary, { props: { connections: [] } });
    expect(wrapper.text()).toBe("");
  });
});
