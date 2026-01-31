import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ConnectionGossipPanel from "../ConnectionGossipPanel.vue";
import type { RelationshipNarrative, NarrativeTrigger } from "@/types/entityProfile";

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
