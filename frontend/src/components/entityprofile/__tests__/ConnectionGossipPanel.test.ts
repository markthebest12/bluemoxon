import { describe, it, expect } from "vitest";
import { mount, RouterLinkStub } from "@vue/test-utils";
import ConnectionGossipPanel from "../ConnectionGossipPanel.vue";
import type {
  RelationshipNarrative,
  NarrativeTrigger,
  ProfileConnection,
} from "@/types/entityProfile";

const proseNarrative: RelationshipNarrative = {
  summary: "A dramatic literary friendship.",
  details: [
    {
      text: "They exchanged passionate letters for years before meeting.",
      year: 1845,
      significance: "revelation",
      tone: "dramatic",
      display_in: ["connection-detail"],
    },
    {
      text: "Their correspondence influenced major poetic works.",
      significance: "notable",
      tone: "intellectual",
      display_in: ["connection-detail"],
    },
  ],
  narrative_style: "prose-paragraph",
};

const bulletNarrative: RelationshipNarrative = {
  summary: "Shared publishing connections.",
  details: [
    {
      text: "Both published with Smith, Elder & Co.",
      year: 1847,
      significance: "context",
      tone: "intellectual",
      display_in: ["connection-detail"],
    },
  ],
  narrative_style: "bullet-facts",
};

const timelineNarrative: RelationshipNarrative = {
  summary: "A timeline of influence.",
  details: [
    {
      text: "First meeting at a literary salon.",
      year: 1840,
      significance: "notable",
      tone: "triumphant",
      display_in: ["connection-detail"],
    },
    {
      text: "Published joint anthology.",
      year: 1852,
      significance: "revelation",
      tone: "intellectual",
      display_in: ["connection-detail"],
    },
  ],
  narrative_style: "timeline-events",
};

describe("ConnectionGossipPanel", () => {
  it("renders summary text", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.text()).toContain("A dramatic literary friendship.");
  });

  it("renders detail facts", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.text()).toContain("exchanged passionate letters");
  });

  it("renders year badge on dated facts", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.text()).toContain("1845");
  });

  it("renders trigger badge when present", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: "cross_era_bridge" as NarrativeTrigger },
    });
    expect(wrapper.text()).toContain("Cross-Era Bridge");
  });

  it("does not render trigger badge when null", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel__trigger").exists()).toBe(false);
  });

  it("applies prose-paragraph render mode", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel--prose-paragraph").exists()).toBe(true);
  });

  it("applies bullet-facts render mode", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: bulletNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel--bullet-facts").exists()).toBe(true);
  });

  it("applies timeline-events render mode", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: timelineNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel--timeline-events").exists()).toBe(true);
  });

  it("renders timeline years in order", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: timelineNarrative, trigger: null },
    });
    const text = wrapper.text();
    expect(text.indexOf("1840")).toBeLessThan(text.indexOf("1852"));
  });

  it("handles empty details gracefully", () => {
    const emptyNarrative: RelationshipNarrative = {
      summary: "A brief connection.",
      details: [],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: emptyNarrative, trigger: null },
    });
    expect(wrapper.text()).toContain("A brief connection.");
    expect(wrapper.find(".gossip-panel__prose").exists()).toBe(false);
  });
});

const gossipConnections: ProfileConnection[] = [
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

describe("ConnectionGossipPanel cross-link integration", () => {
  const globalStubs = { stubs: { RouterLink: RouterLinkStub } };

  it("renders cross-link in summary as a router-link", () => {
    const narrative: RelationshipNarrative = {
      summary: "A dramatic friendship with {{entity:author:32|Robert Browning}}.",
      details: [],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Robert Browning");
  });

  it("renders cross-link in summary with correct route params", () => {
    const narrative: RelationshipNarrative = {
      summary: "Both published with {{entity:publisher:7|Smith, Elder & Co.}}.",
      details: [],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const link = wrapper.findComponent(RouterLinkStub);
    expect(link.props("to")).toEqual({
      name: "entity-profile",
      params: { type: "publisher", id: "7" },
    });
  });

  it("renders cross-links in prose-paragraph detail facts", () => {
    const narrative: RelationshipNarrative = {
      summary: "A literary partnership.",
      details: [
        {
          text: "Met {{entity:author:32|Robert Browning}} at a London salon.",
          year: 1845,
          significance: "revelation",
          tone: "dramatic",
          display_in: ["connection-detail"],
        },
      ],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Robert Browning");
  });

  it("renders cross-links in bullet-facts detail items", () => {
    const narrative: RelationshipNarrative = {
      summary: "Shared publishing connections.",
      details: [
        {
          text: "Both worked with {{entity:publisher:7|Smith, Elder & Co.}} on first editions.",
          year: 1847,
          significance: "context",
          tone: "intellectual",
          display_in: ["connection-detail"],
        },
      ],
      narrative_style: "bullet-facts",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Smith, Elder & Co.");
  });

  it("renders cross-links in timeline-events detail items", () => {
    const narrative: RelationshipNarrative = {
      summary: "A timeline of influence.",
      details: [
        {
          text: "First meeting with {{entity:author:32|Robert Browning}} at a literary gathering.",
          year: 1840,
          significance: "notable",
          tone: "triumphant",
          display_in: ["connection-detail"],
        },
      ],
      narrative_style: "timeline-events",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Robert Browning");
  });

  it("renders multiple cross-links across summary and details", () => {
    const narrative: RelationshipNarrative = {
      summary: "A connection between {{entity:author:32|Robert Browning}} and their publisher.",
      details: [
        {
          text: "Both published through {{entity:publisher:7|Smith, Elder & Co.}} in the 1840s.",
          year: 1847,
          significance: "context",
          tone: "intellectual",
          display_in: ["connection-detail"],
        },
      ],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(2);
    expect(links[0].text()).toBe("Robert Browning");
    expect(links[1].text()).toBe("Smith, Elder & Co.");
  });

  it("renders stale marker as plain text when connection is missing", () => {
    const narrative: RelationshipNarrative = {
      summary: "Influenced by {{entity:author:999|Percy Shelley}} in early work.",
      details: [],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    expect(wrapper.text()).toContain("Percy Shelley");
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(0);
  });

  it("does not render cross-links when connections prop is omitted", () => {
    const narrative: RelationshipNarrative = {
      summary: "A friendship with {{entity:author:32|Robert Browning}}.",
      details: [],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null },
      global: globalStubs,
    });

    expect(wrapper.text()).toContain("Robert Browning");
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(0);
  });

  it("preserves surrounding text around cross-links in details", () => {
    const narrative: RelationshipNarrative = {
      summary: "Literary partners.",
      details: [
        {
          text: "She eloped with {{entity:author:32|Robert Browning}} to Florence in 1846.",
          year: 1846,
          significance: "revelation",
          tone: "dramatic",
          display_in: ["connection-detail"],
        },
      ],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const text = wrapper.text();
    expect(text).toContain("She eloped with");
    expect(text).toContain("Robert Browning");
    expect(text).toContain("to Florence in 1846.");
  });

  it("renders cross-link with entity-linked-text__link class", () => {
    const narrative: RelationshipNarrative = {
      summary: "Met {{entity:author:32|Robert Browning}} through mutual friends.",
      details: [],
      narrative_style: "prose-paragraph",
    };
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative, trigger: null, connections: gossipConnections },
      global: globalStubs,
    });

    const link = wrapper.findComponent(RouterLinkStub);
    expect(link.classes()).toContain("entity-linked-text__link");
  });
});
