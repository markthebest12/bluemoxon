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

describe("EntityBooks — Thumbnails & Badges", () => {
  const booksWithImages: ProfileBook[] = [
    {
      id: 59,
      title: "Aurora Leigh",
      year: 1877,
      condition: "NEAR_FINE",
      edition: "American reprint",
      primary_image_url: "https://cdn.example.com/books/59/primary.jpg",
    },
    {
      id: 608,
      title: "Sonnets from the Portuguese",
      year: 1920,
      condition: "VERY_GOOD",
      primary_image_url: "https://cdn.example.com/books/608/primary.jpg",
    },
  ];

  it("renders thumbnail image with correct src for each book", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: booksWithImages },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    const thumbnails = wrapper.findAll("[data-testid='book-thumbnail']");
    expect(thumbnails).toHaveLength(2);
    expect(thumbnails[0].attributes("src")).toBe("https://cdn.example.com/books/59/primary.jpg");
    expect(thumbnails[1].attributes("src")).toBe("https://cdn.example.com/books/608/primary.jpg");
  });

  it("renders ConditionBadge for each book with condition", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: booksWithImages },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    const badges = wrapper.findAll(".condition-badge");
    expect(badges).toHaveLength(2);
  });

  it("shows no badge when book has no condition", () => {
    const booksNoCondition: ProfileBook[] = [
      { id: 1, title: "Poems", year: 1844, primary_image_url: "https://cdn.example.com/1.jpg" },
    ];
    const wrapper = mount(EntityBooks, {
      props: { books: booksNoCondition },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.find(".condition-badge").exists()).toBe(false);
  });

  it("show-all toggle still works with thumbnails", async () => {
    const manyBooks: ProfileBook[] = Array.from({ length: 10 }, (_, i) => ({
      id: i,
      title: `Book ${i}`,
      condition: "GOOD",
      primary_image_url: `https://cdn.example.com/${i}.jpg`,
    }));
    const wrapper = mount(EntityBooks, {
      props: { books: manyBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    // Initially only 6 visible
    expect(wrapper.findAll("[data-testid='book-thumbnail']")).toHaveLength(6);
    await wrapper.find(".entity-books__show-all").trigger("click");
    expect(wrapper.findAll("[data-testid='book-thumbnail']")).toHaveLength(10);
  });
});
