import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import PublicationTimeline from "../PublicationTimeline.vue";

const mockRouter = { push: vi.fn() };

vi.mock("vue-router", () => ({
  useRouter: () => mockRouter,
}));

const mockBooks = [
  { id: 57, title: "Poetical Works", year: 1904, condition: "VERY_GOOD", edition: "Oxford" },
  { id: 59, title: "Aurora Leigh", year: 1877, condition: "NEAR_FINE", edition: "Reprint" },
];

describe("PublicationTimeline", () => {
  it("navigates to book detail on dot click", async () => {
    mockRouter.push.mockClear();
    const wrapper = mount(PublicationTimeline, {
      props: { books: mockBooks },
    });

    // dots[0] corresponds to mockBooks[0] (id 57) because booksWithYears
    // preserves input order (filter only, no sort).
    const dots = wrapper.findAll(".publication-timeline__dot");
    expect(dots.length).toBeGreaterThan(0);
    await dots[0].trigger("click");
    expect(mockRouter.push).toHaveBeenCalledWith({
      name: "book-detail",
      params: { id: "57" },
    });
  });

  it("does not navigate when no books", () => {
    const wrapper = mount(PublicationTimeline, {
      props: { books: [] },
    });
    expect(wrapper.find(".publication-timeline__dot").exists()).toBe(false);
  });
});

describe("PublicationTimeline — Tooltip Enhancements", () => {
  it("tooltip includes thumbnail image when hovered", async () => {
    const booksWithImages = [
      {
        id: 57,
        title: "Poetical Works",
        year: 1904,
        condition: "VERY_GOOD",
        primary_image_url: "https://cdn.example.com/57.jpg",
      },
      {
        id: 59,
        title: "Aurora Leigh",
        year: 1877,
        condition: "NEAR_FINE",
        primary_image_url: "https://cdn.example.com/59.jpg",
      },
    ];
    const wrapper = mount(PublicationTimeline, { props: { books: booksWithImages } });
    const dots = wrapper.findAll(".publication-timeline__dot");
    await dots[0].trigger("mouseenter");
    const tooltip = wrapper.find(".publication-timeline__tooltip");
    const img = tooltip.find("[data-testid='tooltip-thumbnail']");
    expect(img.exists()).toBe(true);
    expect(img.attributes("src")).toBe("https://cdn.example.com/57.jpg");
  });

  it("tooltip includes condition badge when hovered", async () => {
    const booksWithCondition = [
      {
        id: 57,
        title: "Poetical Works",
        year: 1904,
        condition: "VERY_GOOD",
        primary_image_url: "https://cdn.example.com/57.jpg",
      },
      { id: 59, title: "Aurora Leigh", year: 1877, condition: "NEAR_FINE" },
    ];
    const wrapper = mount(PublicationTimeline, { props: { books: booksWithCondition } });
    const dots = wrapper.findAll(".publication-timeline__dot");
    await dots[0].trigger("mouseenter");
    expect(wrapper.find(".publication-timeline__tooltip .condition-badge").exists()).toBe(true);
  });
});
