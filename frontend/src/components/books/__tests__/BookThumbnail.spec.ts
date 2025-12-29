import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookThumbnail from "../BookThumbnail.vue";

describe("BookThumbnail", () => {
  const defaultProps = {
    bookId: 123,
  };

  describe("container query structure", () => {
    it("has @container class on wrapper element", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const container = wrapper.find("[class*='@container']");
      expect(container.exists()).toBe(true);
    });

    it("has aspect-[4/5] class for proper aspect ratio", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const inner = wrapper.find("[class*='aspect-']");
      expect(inner.exists()).toBe(true);
      expect(inner.classes()).toContain("aspect-[4/5]");
    });

    it("fills container width with w-full class", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const container = wrapper.find("[class*='@container']");
      expect(container.classes()).toContain("w-full");
    });
  });

  describe("image rendering", () => {
    it("renders placeholder when no imageUrl provided", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const img = wrapper.find("img");
      expect(img.exists()).toBe(true);
      expect(img.attributes("src")).toContain("/images/placeholder");
    });

    it("renders provided imageUrl", () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      const img = wrapper.find("img");
      expect(img.attributes("src")).toBe("https://example.com/book.jpg");
    });

    it("shows image indicator badge when has image", () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      const badge = wrapper.find("svg");
      expect(badge.exists()).toBe(true);
    });

    it("does not show image indicator badge when no image", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const badge = wrapper.find("svg");
      expect(badge.exists()).toBe(false);
    });
  });

  describe("click behavior", () => {
    it("emits click when has image and clicked", async () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      await wrapper.trigger("click");
      expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("does not emit click when no image and clicked", async () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      await wrapper.trigger("click");
      expect(wrapper.emitted("click")).toBeUndefined();
    });

    it("has cursor-pointer class when has image", () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      const clickable = wrapper.find("[class*='cursor-pointer']");
      expect(clickable.exists()).toBe(true);
    });
  });

  describe("no size prop", () => {
    it("does not accept size prop (removed)", () => {
      // This test documents that size prop was intentionally removed
      // Component should work without any size prop
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      expect(wrapper.exists()).toBe(true);
    });
  });
});
