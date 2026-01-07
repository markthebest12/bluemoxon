import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { RouterLinkStub } from "@vue/test-utils";
import BookActionsBar from "../BookActionsBar.vue";

describe("BookActionsBar", () => {
  const mockBook = {
    id: 123,
    title: "Test Book",
  };

  const defaultProps = {
    book: mockBook,
    isEditor: false,
  };

  const mountOptions = {
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
      },
    },
  };

  describe("print button", () => {
    it("renders print button for all users", () => {
      const wrapper = mount(BookActionsBar, {
        props: defaultProps,
        ...mountOptions,
      });
      const printButton = wrapper.find('button[title="Print this page"]');
      expect(printButton.exists()).toBe(true);
    });

    it("emits print when print button clicked", async () => {
      const wrapper = mount(BookActionsBar, {
        props: defaultProps,
        ...mountOptions,
      });
      const printButton = wrapper.find('button[title="Print this page"]');
      await printButton.trigger("click");
      expect(wrapper.emitted("print")).toHaveLength(1);
    });
  });

  describe("editor actions", () => {
    it("shows Edit link when isEditor is true", () => {
      const wrapper = mount(BookActionsBar, {
        props: { ...defaultProps, isEditor: true },
        ...mountOptions,
      });
      const editLink = wrapper.findComponent(RouterLinkStub);
      expect(editLink.exists()).toBe(true);
      expect(editLink.text()).toBe("Edit Book");
    });

    it("Edit link points to correct route /books/{id}/edit", () => {
      const wrapper = mount(BookActionsBar, {
        props: { ...defaultProps, isEditor: true },
        ...mountOptions,
      });
      const editLink = wrapper.findComponent(RouterLinkStub);
      expect(editLink.props("to")).toBe("/books/123/edit");
    });

    it("shows Delete button when isEditor is true", () => {
      const wrapper = mount(BookActionsBar, {
        props: { ...defaultProps, isEditor: true },
        ...mountOptions,
      });
      const deleteButton = wrapper.findAll("button").find((btn) => btn.text() === "Delete");
      expect(deleteButton).toBeDefined();
    });

    it("emits delete when delete button clicked", async () => {
      const wrapper = mount(BookActionsBar, {
        props: { ...defaultProps, isEditor: true },
        ...mountOptions,
      });
      const deleteButton = wrapper.findAll("button").find((btn) => btn.text() === "Delete");
      await deleteButton!.trigger("click");
      expect(wrapper.emitted("delete")).toHaveLength(1);
    });
  });

  describe("non-editor user", () => {
    it("hides Edit link when isEditor is false", () => {
      const wrapper = mount(BookActionsBar, {
        props: { ...defaultProps, isEditor: false },
        ...mountOptions,
      });
      const editLink = wrapper.findComponent(RouterLinkStub);
      expect(editLink.exists()).toBe(false);
    });

    it("hides Delete button when isEditor is false", () => {
      const wrapper = mount(BookActionsBar, {
        props: { ...defaultProps, isEditor: false },
        ...mountOptions,
      });
      const deleteButton = wrapper.findAll("button").find((btn) => btn.text() === "Delete");
      expect(deleteButton).toBeUndefined();
    });
  });
});
