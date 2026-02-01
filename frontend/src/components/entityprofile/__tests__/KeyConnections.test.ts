import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import KeyConnections from "../KeyConnections.vue";
import type { ProfileConnection } from "@/types/entityProfile";

const connWithStory: ProfileConnection = {
  entity: { id: 31, type: "author", name: "Elizabeth Barrett Browning" },
  connection_type: "literary_associate",
  strength: 8,
  shared_book_count: 3,
  shared_books: [{ id: 1, title: "Aurora Leigh", year: 1856 }],
  narrative: "Close literary associates.",
  narrative_trigger: "cross_era_bridge",
  is_key: true,
  relationship_story: {
    summary: "A dramatic literary friendship.",
    details: [
      {
        text: "They exchanged passionate letters.",
        year: 1845,
        significance: "revelation",
        tone: "dramatic",
        display_in: ["connection-detail"],
      },
    ],
    narrative_style: "prose-paragraph",
  },
};

const connWithoutStory: ProfileConnection = {
  entity: { id: 7, type: "publisher", name: "Smith, Elder & Co." },
  connection_type: "publisher",
  strength: 6,
  shared_book_count: 5,
  shared_books: [],
  narrative: "Published several works.",
  narrative_trigger: null,
  is_key: true,
  relationship_story: null,
};

// Stub router-link to avoid router dependency in unit tests
const stubs = {
  "router-link": {
    template: "<a><slot /></a>",
    props: ["to"],
  },
};

describe("KeyConnections", () => {
  it("renders connection names", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory, connWithoutStory] },
      global: { stubs },
    });
    expect(wrapper.text()).toContain("Elizabeth Barrett Browning");
    expect(wrapper.text()).toContain("Smith, Elder & Co.");
  });

  it("shows 'View full story' button only when relationship_story exists", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory, connWithoutStory] },
      global: { stubs },
    });
    const buttons = wrapper.findAll(".key-connections__story-toggle");
    expect(buttons).toHaveLength(1);
  });

  it("expands gossip panel on button click", async () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory] },
      global: { stubs },
    });
    expect(wrapper.find(".gossip-panel").exists()).toBe(false);
    await wrapper.find(".key-connections__story-toggle").trigger("click");
    expect(wrapper.find(".gossip-panel").exists()).toBe(true);
  });

  it("collapses gossip panel on second click", async () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory] },
      global: { stubs },
    });
    const btn = wrapper.find(".key-connections__story-toggle");
    await btn.trigger("click");
    expect(wrapper.find(".gossip-panel").exists()).toBe(true);
    await btn.trigger("click");
    expect(wrapper.find(".gossip-panel").exists()).toBe(false);
  });

  it("renders gossip panel content when expanded", async () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory] },
      global: { stubs },
    });
    await wrapper.find(".key-connections__story-toggle").trigger("click");
    expect(wrapper.text()).toContain("A dramatic literary friendship.");
    expect(wrapper.text()).toContain("exchanged passionate letters");
  });

  it("renders shared books as links to book detail", () => {
    const wrapper = mount(KeyConnections, {
      props: {
        connections: [
          {
            entity: { id: 31, type: "author", name: "EBB" },
            connection_type: "shared_publisher",
            strength: 5,
            shared_book_count: 1,
            shared_books: [{ id: 57, title: "Poetical Works", year: 1904 }],
            narrative: null,
            narrative_trigger: null,
            is_key: true,
            relationship_story: null,
          },
        ],
      },
      global: {
        stubs: {
          "router-link": {
            template: '<a :data-to="JSON.stringify(to)"><slot /></a>',
            props: ["to"],
          },
        },
      },
    });

    const bookLinks = wrapper.findAll(".key-connections__book-link");
    expect(bookLinks.length).toBe(1);
    const to = JSON.parse(bookLinks[0].attributes("data-to")!);
    expect(to.name).toBe("book-detail");
    expect(to.params.id).toBe("57");
  });
});
