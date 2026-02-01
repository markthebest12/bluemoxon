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
