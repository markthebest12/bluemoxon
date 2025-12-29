import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookThumbnail from "../BookThumbnail.vue";

describe("BookThumbnail", () => {
  const defaultProps = {
    bookId: 123,
  };

  describe("layout structure", () => {
    it("has aspect-[4/5] class for proper aspect ratio", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      expect(wrapper.classes()).toContain("aspect-[4/5]");
    });

    it("fills container width with w-full class", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      expect(wrapper.classes()).toContain("w-full");
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
      expect(wrapper.classes()).toContain("cursor-pointer");
    });

    it("does not have cursor-pointer class when no image", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      expect(wrapper.classes()).not.toContain("cursor-pointer");
    });
  });
});
