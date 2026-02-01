import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import EntityBooks from "../EntityBooks.vue";
import type { ProfileBook } from "@/types/entityProfile";

const mockBooks: ProfileBook[] = [
  {
    id: 59,
    title: "Aurora Leigh",
    year: 1877,
    condition: "Near Fine",
    edition: "American reprint",
  },
  { id: 608, title: "Sonnets from the Portuguese", year: 1920, condition: "VG+" },
];

describe("EntityBooks", () => {
  it("renders book count in title", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: mockBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("Books in Collection (2)");
  });

  it("renders all book titles", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: mockBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("Aurora Leigh");
    expect(wrapper.text()).toContain("Sonnets from the Portuguese");
  });

  it("shows 'Show all' button when more than 6 books", () => {
    const manyBooks: ProfileBook[] = Array.from({ length: 10 }, (_, i) => ({
      id: i,
      title: `Book ${i}`,
    }));
    const wrapper = mount(EntityBooks, {
      props: { books: manyBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("Show all 10 books");
  });

  it("formats raw condition enum values as human-readable text", () => {
    const rawBooks: ProfileBook[] = [
      { id: 1, title: "Aurora Leigh", year: 1856, condition: "NEAR_FINE", edition: "First" },
      { id: 2, title: "Sonnets", year: 1850, condition: "VERY_GOOD" },
    ];
    const wrapper = mount(EntityBooks, {
      props: { books: rawBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("Near Fine");
    expect(wrapper.text()).not.toContain("NEAR_FINE");
    expect(wrapper.text()).toContain("Very Good");
    expect(wrapper.text()).not.toContain("VERY_GOOD");
  });

  it("handles null condition gracefully", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: [{ id: 3, title: "Poems", year: 1844 }] },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).not.toContain("null");
    expect(wrapper.text()).not.toContain("undefined");
  });
});
