import { describe, it, expect } from "vitest";
import { mount, RouterLinkStub } from "@vue/test-utils";
import EntityLinkedText from "../EntityLinkedText.vue";
import type { ProfileConnection } from "@/types/entityProfile";

const mockConnections: ProfileConnection[] = [
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
];

describe("EntityLinkedText", () => {
  it("renders plain text when no markers", () => {
    const wrapper = mount(EntityLinkedText, {
      props: { text: "Plain text here.", connections: [] },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    expect(wrapper.text()).toBe("Plain text here.");
    expect(wrapper.findAllComponents(RouterLinkStub)).toHaveLength(0);
  });

  it("renders link for valid marker with matching connection", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "Met {{entity:author:32|Robert Browning}} at a salon.",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Robert Browning");
  });

  it("renders plain text for marker with no matching connection (stale)", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "Met {{entity:author:999|Ghost Person}} at a salon.",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    expect(wrapper.text()).toContain("Ghost Person");
    expect(wrapper.findAllComponents(RouterLinkStub)).toHaveLength(0);
  });

  it("renders link with correct route params", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "{{entity:author:32|Robert Browning}}",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const link = wrapper.findComponent(RouterLinkStub);
    // RouterLinkStub stores the `to` prop
    expect(link.props("to")).toEqual({
      name: "entity-profile",
      params: { type: "author", id: "32" },
    });
  });

  it("applies entity-link class to links", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "{{entity:author:32|Robert Browning}}",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const link = wrapper.findComponent(RouterLinkStub);
    expect(link.classes()).toContain("entity-linked-text__link");
  });
});
