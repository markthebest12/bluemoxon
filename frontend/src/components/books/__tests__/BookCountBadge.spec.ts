import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookCountBadge from "../BookCountBadge.vue";

describe("BookCountBadge", () => {
  describe("count display", () => {
    it("displays the count number", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      expect(wrapper.text()).toContain("42");
    });

    it("displays zero count", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 0 } });
      expect(wrapper.text()).toContain("0");
    });

    it("displays large counts", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 1234 } });
      expect(wrapper.text()).toContain("1234");
    });
  });

  describe("label display", () => {
    it("shows 'books' label on desktop (sm: breakpoint)", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      const label = wrapper.find('[data-testid="books-label"]');
      expect(label.exists()).toBe(true);
      expect(label.text()).toBe("books");
    });

    it("label has responsive visibility class", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      const label = wrapper.find('[data-testid="books-label"]');
      expect(label.classes()).toContain("hidden");
      expect(label.classes()).toContain("sm:inline");
    });
  });

  describe("flourish decorations", () => {
    it("displays flourish characters", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      const flourishes = wrapper.findAll('[data-testid="flourish"]');
      expect(flourishes.length).toBe(2);
    });

    it("flourishes have responsive visibility", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      const flourishes = wrapper.findAll('[data-testid="flourish"]');
      flourishes.forEach((flourish) => {
        expect(flourish.classes()).toContain("hidden");
        expect(flourish.classes()).toContain("sm:inline");
      });
    });

    it("flourishes contain the star character", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      const flourishes = wrapper.findAll('[data-testid="flourish"]');
      flourishes.forEach((flourish) => {
        expect(flourish.text()).toBe("✦");
      });
    });
  });

  describe("styling", () => {
    it("has badge container styling", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      expect(wrapper.classes()).toContain("book-count-badge");
    });

    it("has pill shape with rounded-full", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      expect(wrapper.classes()).toContain("rounded-full");
    });

    it("has proper padding", () => {
      const wrapper = mount(BookCountBadge, { props: { count: 42 } });
      expect(wrapper.classes()).toContain("px-3");
      expect(wrapper.classes()).toContain("py-1");
    });
  });
});
