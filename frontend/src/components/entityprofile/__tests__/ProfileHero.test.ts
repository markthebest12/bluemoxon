import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ProfileHero from "../ProfileHero.vue";
import type { ProfileEntity, ProfileData } from "@/types/entityProfile";

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

describe("ProfileHero", () => {
  it("renders entity name", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("Elizabeth Barrett Browning");
  });

  it("renders tier label from formatTier", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("Premier");
  });

  it("renders date range for authors", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("1806");
    expect(wrapper.text()).toContain("1861");
  });

  it("renders bio summary", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("One of the most prominent Victorian poets.");
  });

  it("renders personal stories filtered to hero-bio", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("domineering father");
  });

  it("shows placeholder when no bio", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: null },
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
    });
    expect(wrapper.text()).toContain("Est. 1816");
  });
});
