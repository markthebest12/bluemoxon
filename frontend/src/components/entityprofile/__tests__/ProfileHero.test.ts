import { describe, it, expect } from "vitest";
import { mount, RouterLinkStub } from "@vue/test-utils";
import ProfileHero from "../ProfileHero.vue";
import type { ProfileEntity, ProfileData } from "@/types/entityProfile";
import { mockCrossLinkConnections } from "./crossLinkFixtures";

const mockAuthor: ProfileEntity = {
  id: 31,
  type: "author",
  name: "Elizabeth Barrett Browning",
  birth_year: 1806,
  death_year: 1861,
  era: "romantic",
  tier: "TIER_1",
};

const mockProfile: ProfileData = {
  bio_summary: "One of the most prominent Victorian poets.",
  personal_stories: [
    {
      text: "Her domineering father forbade all of his children from marrying.",
      year: 1835,
      significance: "context",
      tone: "dramatic",
      display_in: ["hero-bio"],
    },
  ],
  is_stale: false,
  generated_at: "2026-01-29T10:00:00Z",
  model_version: "claude-3-5-haiku-20241022",
};

const mockConnections = mockCrossLinkConnections;

describe("ProfileHero", () => {
  const globalStubs = { stubs: { RouterLink: RouterLinkStub } };

  it("renders entity name", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
      global: globalStubs,
    });
    expect(wrapper.text()).toContain("Elizabeth Barrett Browning");
  });

  it("renders tier label from formatTier", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
      global: globalStubs,
    });
    expect(wrapper.text()).toContain("Premier");
  });

  it("renders date range for authors", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
      global: globalStubs,
    });
    expect(wrapper.text()).toContain("1806");
    expect(wrapper.text()).toContain("1861");
  });

  it("renders bio summary", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
      global: globalStubs,
    });
    expect(wrapper.text()).toContain("One of the most prominent Victorian poets.");
  });

  it("renders personal stories filtered to hero-bio", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
      global: globalStubs,
    });
    expect(wrapper.text()).toContain("domineering father");
  });

  it("shows placeholder when no bio", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: null },
      global: globalStubs,
    });
    expect(wrapper.text()).toContain("not yet generated");
  });

  it("renders founded year for publishers", () => {
    const publisher: ProfileEntity = {
      id: 7,
      type: "publisher",
      name: "Smith, Elder & Co.",
      founded_year: 1816,
      tier: "TIER_1",
    };
    const wrapper = mount(ProfileHero, {
      props: { entity: publisher, profile: null },
      global: globalStubs,
    });
    expect(wrapper.text()).toContain("Est. 1816");
  });
});

describe("ProfileHero cross-link integration", () => {
  const globalStubs = { stubs: { RouterLink: RouterLinkStub } };

  it("renders cross-link in bio_summary as a router-link", () => {
    const profileWithMarker: ProfileData = {
      ...mockProfile,
      bio_summary: "Married {{entity:author:32|Robert Browning}} in 1846 and moved to Italy.",
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithMarker,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Robert Browning");
  });

  it("renders cross-link in bio_summary with correct route params", () => {
    const profileWithMarker: ProfileData = {
      ...mockProfile,
      bio_summary: "Published by {{entity:publisher:7|Smith, Elder & Co.}} throughout her career.",
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithMarker,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    const link = wrapper.findComponent(RouterLinkStub);
    expect(link.props("to")).toEqual({
      name: "entity-profile",
      params: { type: "publisher", id: "7" },
    });
  });

  it("renders multiple cross-links in bio_summary", () => {
    const profileWithMarkers: ProfileData = {
      ...mockProfile,
      bio_summary:
        "Married {{entity:author:32|Robert Browning}} and published with {{entity:publisher:7|Smith, Elder & Co.}}.",
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithMarkers,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(2);
    expect(links[0].text()).toBe("Robert Browning");
    expect(links[1].text()).toBe("Smith, Elder & Co.");
  });

  it("renders stale marker as plain text when connection is missing", () => {
    const profileWithStale: ProfileData = {
      ...mockProfile,
      bio_summary: "Influenced by {{entity:author:999|John Keats}} in her early work.",
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithStale,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    expect(wrapper.text()).toContain("John Keats");
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(0);
  });

  it("renders cross-links in hero-bio personal stories", () => {
    const profileWithStoryMarker: ProfileData = {
      ...mockProfile,
      personal_stories: [
        {
          text: "Eloped with {{entity:author:32|Robert Browning}} to Florence in secret.",
          year: 1846,
          significance: "revelation",
          tone: "dramatic",
          display_in: ["hero-bio"],
        },
      ],
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithStoryMarker,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Robert Browning");
  });

  it("renders cross-links in both bio and stories simultaneously", () => {
    const profileWithBoth: ProfileData = {
      ...mockProfile,
      bio_summary: "Married {{entity:author:32|Robert Browning}} in 1846.",
      personal_stories: [
        {
          text: "Published through {{entity:publisher:7|Smith, Elder & Co.}} in London.",
          year: 1838,
          significance: "context",
          tone: "intellectual",
          display_in: ["hero-bio"],
        },
      ],
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithBoth,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(2);
    expect(links[0].text()).toBe("Robert Browning");
    expect(links[1].text()).toBe("Smith, Elder & Co.");
  });

  it("does not render cross-links when connections prop is omitted", () => {
    const profileWithMarker: ProfileData = {
      ...mockProfile,
      bio_summary: "Married {{entity:author:32|Robert Browning}} in 1846.",
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithMarker,
        // connections omitted — defaults to []
      },
      global: globalStubs,
    });

    // Marker text should still appear, but as plain text (no link)
    expect(wrapper.text()).toContain("Robert Browning");
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(0);
  });

  it("excludes cross-linked stories not in hero-bio display_in", () => {
    const profileWithNonHeroStory: ProfileData = {
      ...mockProfile,
      bio_summary: "A prominent poet.",
      personal_stories: [
        {
          text: "Met {{entity:author:32|Robert Browning}} at a literary gathering.",
          year: 1845,
          significance: "notable",
          tone: "dramatic",
          display_in: ["connection-detail"],
        },
      ],
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithNonHeroStory,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    // Story text should not appear in hero section (wrong display_in)
    expect(wrapper.text()).not.toContain("literary gathering");
    // Only the bio_summary link-free text should render, no router-links
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(0);
  });

  it("preserves surrounding text around cross-links", () => {
    const profileWithMarker: ProfileData = {
      ...mockProfile,
      bio_summary: "She married {{entity:author:32|Robert Browning}} and moved to Italy.",
    };
    const wrapper = mount(ProfileHero, {
      props: {
        entity: mockAuthor,
        profile: profileWithMarker,
        connections: mockConnections,
      },
      global: globalStubs,
    });

    const text = wrapper.text();
    expect(text).toContain("She married");
    expect(text).toContain("Robert Browning");
    expect(text).toContain("and moved to Italy.");
  });
});
