import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import KeyConnections from "../KeyConnections.vue";
import type { ProfileConnection } from "@/types/entityProfile";

const connWithStory: ProfileConnection = {
  entity: { id: 31, type: "author", name: "Elizabeth Barrett Browning", image_url: null },
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
  entity: { id: 7, type: "publisher", name: "Smith, Elder & Co.", image_url: null },
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
            entity: { id: 31, type: "author", name: "EBB", image_url: null },
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

describe("KeyConnections — Thumbnails & Badges", () => {
  it("renders inline thumbnail for shared books with primary_image_url", () => {
    const connWithThumbnails: ProfileConnection = {
      entity: { id: 31, type: "author", name: "EBB", image_url: null },
      connection_type: "literary_associate",
      strength: 5,
      shared_book_count: 2,
      shared_books: [
        {
          id: 1,
          title: "Aurora Leigh",
          year: 1856,
          primary_image_url: "https://cdn.example.com/1.jpg",
          condition: "FINE",
        },
        {
          id: 2,
          title: "Sonnets",
          year: 1850,
          primary_image_url: "https://cdn.example.com/2.jpg",
        },
      ],
      narrative: null,
      narrative_trigger: null,
      is_key: true,
      relationship_story: null,
    };
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithThumbnails] },
      global: { stubs },
    });
    const thumbnails = wrapper.findAll("[data-testid='book-thumbnail']");
    expect(thumbnails).toHaveLength(2);
    expect(thumbnails[0].attributes("src")).toBe("https://cdn.example.com/1.jpg");
  });

  it("renders condition badge inline for shared books with condition", () => {
    const connWithCondition: ProfileConnection = {
      entity: { id: 31, type: "author", name: "EBB", image_url: null },
      connection_type: "literary_associate",
      strength: 5,
      shared_book_count: 1,
      shared_books: [
        {
          id: 1,
          title: "Aurora Leigh",
          year: 1856,
          condition: "NEAR_FINE",
          primary_image_url: "https://cdn.example.com/1.jpg",
        },
      ],
      narrative: null,
      narrative_trigger: null,
      is_key: true,
      relationship_story: null,
    };
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithCondition] },
      global: { stubs },
    });
    expect(wrapper.find(".condition-badge").exists()).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// AI-discovered connection tests
// ---------------------------------------------------------------------------

describe("KeyConnections — AI Badges & Discovery", () => {
  const aiConn: ProfileConnection = {
    entity: { id: 50, type: "author", name: "Percy Bysshe Shelley", image_url: null },
    connection_type: "romantic_partner",
    sub_type: "familial",
    confidence: 0.85,
    is_ai_discovered: true,
    strength: 7,
    shared_book_count: 0,
    shared_books: [],
    narrative: "A passionate literary romance discovered through AI analysis.",
    narrative_trigger: null,
    is_key: true,
    relationship_story: null,
  };

  const bookDerivedConn: ProfileConnection = {
    entity: { id: 7, type: "publisher", name: "Smith, Elder & Co.", image_url: null },
    connection_type: "publisher",
    strength: 6,
    shared_book_count: 5,
    shared_books: [],
    narrative: "Published several works.",
    narrative_trigger: null,
    is_key: true,
    relationship_story: null,
    // is_ai_discovered not set (undefined / falsy)
  };

  it("renders AI badge for AI-discovered connections", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [aiConn] },
      global: { stubs },
    });
    const badge = wrapper.find(".key-connections__ai-badge");
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe("AI");
  });

  it("does NOT render AI badge for book-derived connections", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [bookDerivedConn] },
      global: { stubs },
    });
    expect(wrapper.find(".key-connections__ai-badge").exists()).toBe(false);
  });

  it("renders AI badge only on the AI-discovered card when mixed", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [aiConn, bookDerivedConn] },
      global: { stubs },
    });
    const badges = wrapper.findAll(".key-connections__ai-badge");
    expect(badges).toHaveLength(1);
    // The badge belongs to the first card (Shelley)
    const firstCard = wrapper.findAll(".key-connections__card")[0];
    expect(firstCard.find(".key-connections__ai-badge").exists()).toBe(true);
    const secondCard = wrapper.findAll(".key-connections__card")[1];
    expect(secondCard.find(".key-connections__ai-badge").exists()).toBe(false);
  });

  it("hides 'shared books' count when shared_book_count is 0 for AI-discovered connections", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [aiConn] },
      global: { stubs },
    });
    // The meta section should NOT contain "shared book" text
    const meta = wrapper.find(".key-connections__meta");
    expect(meta.text()).not.toContain("shared book");
  });

  it("shows 'shared books' count when shared_book_count is 0 for non-AI connections", () => {
    const nonAiZeroBooks: ProfileConnection = {
      ...bookDerivedConn,
      shared_book_count: 0,
    };
    const wrapper = mount(KeyConnections, {
      props: { connections: [nonAiZeroBooks] },
      global: { stubs },
    });
    const meta = wrapper.find(".key-connections__meta");
    expect(meta.text()).toContain("0 shared books");
  });

  it("shows 'shared books' count when shared_book_count > 0 for AI-discovered connections", () => {
    const aiWithBooks: ProfileConnection = {
      ...aiConn,
      shared_book_count: 2,
    };
    const wrapper = mount(KeyConnections, {
      props: { connections: [aiWithBooks] },
      global: { stubs },
    });
    const meta = wrapper.find(".key-connections__meta");
    expect(meta.text()).toContain("2 shared books");
  });

  it("renders sub_type badge when sub_type is present", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [aiConn] },
      global: { stubs },
    });
    const subType = wrapper.find(".key-connections__sub-type");
    expect(subType.exists()).toBe(true);
    expect(subType.text()).toBe("familial");
  });

  it("does NOT render sub_type badge when sub_type is absent", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [bookDerivedConn] },
      global: { stubs },
    });
    expect(wrapper.find(".key-connections__sub-type").exists()).toBe(false);
  });

  it("applies rumored narrative style when confidence is below 0.3", () => {
    const lowConfConn: ProfileConnection = {
      ...aiConn,
      confidence: 0.2,
      narrative: "A rumored connection between the two poets.",
    };
    const wrapper = mount(KeyConnections, {
      props: { connections: [lowConfConn] },
      global: { stubs },
    });
    expect(wrapper.find(".key-connections__narrative--rumored").exists()).toBe(true);
  });

  it("does NOT apply rumored narrative style when confidence is 0.3 or above", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [aiConn] }, // confidence: 0.85
      global: { stubs },
    });
    expect(wrapper.find(".key-connections__narrative--rumored").exists()).toBe(false);
  });

  it("does NOT apply rumored narrative style when confidence is undefined", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [bookDerivedConn] },
      global: { stubs },
    });
    expect(wrapper.find(".key-connections__narrative--rumored").exists()).toBe(false);
  });
});
