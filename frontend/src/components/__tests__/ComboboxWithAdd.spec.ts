import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ComboboxWithAdd from "../ComboboxWithAdd.vue";

describe("ComboboxWithAdd", () => {
  const options = [
    { id: 1, name: "Option A" },
    { id: 2, name: "Option B" },
  ];

  it("renders with label", () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    expect(wrapper.text()).toContain("Author");
  });

  it("filters options as user types", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.setValue("Option A");
    // Should show filtered option
    expect(wrapper.text()).toContain("Option A");
    expect(wrapper.text()).not.toContain("Option B");
  });

  it("shows add new option when no match", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.setValue("New Name");
    expect(wrapper.text()).toContain('+ Add "New Name"');
  });

  it("emits update:modelValue when option selected", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.trigger("focus");
    const optionButtons = wrapper.findAll('[data-testid="option"]');
    await optionButtons[0].trigger("mousedown");
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")![0]).toEqual([1]);
  });

  it("emits create when add new clicked", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.setValue("Brand New");
    const addButton = wrapper.find('[data-testid="add-new"]');
    await addButton.trigger("mousedown");
    expect(wrapper.emitted("create")).toBeTruthy();
    expect(wrapper.emitted("create")![0]).toEqual(["Brand New"]);
  });

  describe("suggestedName behavior", () => {
    it("pre-populates input with suggestedName", () => {
      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options,
          modelValue: null,
          suggestedName: "John Doe",
        },
      });
      const input = wrapper.find("input");
      expect((input.element as HTMLInputElement).value).toBe("John Doe");
    });

    it("preserves suggestedName on focus instead of clearing", async () => {
      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options,
          modelValue: null,
          suggestedName: "Suggested Author",
        },
      });
      const input = wrapper.find("input");

      // Trigger focus
      await input.trigger("focus");

      // Value should still be there (not cleared)
      expect((input.element as HTMLInputElement).value).toBe("Suggested Author");
    });

    it("restores suggestedName on blur if field is empty", async () => {
      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options,
          modelValue: null,
          suggestedName: "John Doe",
        },
      });
      const input = wrapper.find("input");

      // Clear the field
      await input.setValue("");

      // Trigger blur
      await input.trigger("blur");

      // Wait for the blur timeout (200ms in the component)
      await new Promise((resolve) => setTimeout(resolve, 250));

      // Should restore the suggested name
      expect((input.element as HTMLInputElement).value).toBe("John Doe");
    });

    it("does not restore suggestedName if user typed something", async () => {
      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options,
          modelValue: null,
          suggestedName: "John Doe",
        },
      });
      const input = wrapper.find("input");

      // User types different value
      await input.setValue("Different Name");

      // Trigger blur
      await input.trigger("blur");

      // Wait for the blur timeout
      await new Promise((resolve) => setTimeout(resolve, 250));

      // Should keep user's input
      expect((input.element as HTMLInputElement).value).toBe("Different Name");
    });

    it("shows add new button for suggestedName when no match in options", async () => {
      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Publisher",
          options,
          modelValue: null,
          suggestedName: "New Publisher",
        },
      });

      // Trigger focus to open dropdown
      const input = wrapper.find("input");
      await input.trigger("focus");

      // Should show add new option for the suggested name
      expect(wrapper.text()).toContain('+ Add "New Publisher"');
    });
  });

  describe("createFn prop with 409 handling", () => {
    it("shows suggestions when createFn returns 409", async () => {
      const createFn = vi.fn().mockRejectedValue({
        response: {
          status: 409,
          data: {
            error: "similar_entity_exists",
            entity_type: "author",
            input: "Macmillan",
            suggestions: [{ id: 123, name: "Macmillan and Co.", match: 0.85, book_count: 42 }],
            resolution: "Use existing",
          },
        },
      });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Publisher",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Macmillan");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");

      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain("Similar");
      expect(wrapper.text()).toContain("Macmillan and Co.");
      expect(wrapper.text()).toContain("85%");
      expect(wrapper.text()).toContain("42 books");
    });

    it("hides book count when zero", async () => {
      const createFn = vi.fn().mockRejectedValue({
        response: {
          status: 409,
          data: {
            error: "similar_entity_exists",
            entity_type: "author",
            input: "Test",
            suggestions: [{ id: 1, name: "Test Author", match: 0.9, book_count: 0 }],
            resolution: "Use existing",
          },
        },
      });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Test");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain("90%");
      expect(wrapper.text()).not.toContain("0 books");
    });

    it("selects suggestion and emits update:modelValue", async () => {
      const createFn = vi.fn().mockRejectedValue({
        response: {
          status: 409,
          data: {
            error: "similar_entity_exists",
            entity_type: "author",
            input: "Test",
            suggestions: [{ id: 99, name: "Existing Author", match: 0.95, book_count: 5 }],
            resolution: "Use existing",
          },
        },
      });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [{ id: 99, name: "Existing Author" }],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Test");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      const useButton = wrapper.find('[data-testid="use-suggestion"]');
      await useButton.trigger("click");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual([99]);
    });

    it("force creates when clicking create anyway link", async () => {
      const createFn = vi
        .fn()
        .mockRejectedValueOnce({
          response: {
            status: 409,
            data: {
              error: "similar_entity_exists",
              entity_type: "author",
              input: "New Author",
              suggestions: [{ id: 1, name: "Similar", match: 0.8, book_count: 3 }],
              resolution: "Use existing",
            },
          },
        })
        .mockResolvedValueOnce({ id: 50, name: "New Author" });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("New Author");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      const createAnywayLink = wrapper.find('[data-testid="create-anyway"]');
      await createAnywayLink.trigger("click");
      await wrapper.vm.$nextTick();

      expect(createFn).toHaveBeenCalledTimes(2);
      expect(createFn).toHaveBeenLastCalledWith("New Author", true);
      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    });

    it("calls createFn on add when provided instead of emitting create", async () => {
      const createFn = vi.fn().mockResolvedValue({ id: 10, name: "Created" });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("New Name");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      expect(createFn).toHaveBeenCalledWith("New Name", false);
      expect(wrapper.emitted("create")).toBeFalsy();
      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual([10]);
    });

    it("still emits create when createFn not provided (backward compat)", async () => {
      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Brand New");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");

      expect(wrapper.emitted("create")).toBeTruthy();
      expect(wrapper.emitted("create")![0]).toEqual(["Brand New"]);
    });

    it("clears conflict state when selecting from dropdown", async () => {
      const createFn = vi.fn().mockRejectedValue({
        response: {
          status: 409,
          data: {
            error: "similar_entity_exists",
            entity_type: "author",
            input: "Test",
            suggestions: [{ id: 1, name: "Similar", match: 0.8, book_count: 0 }],
            resolution: "Use existing",
          },
        },
      });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [{ id: 2, name: "Different Author" }],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Test");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain("Similar");

      // Select from regular dropdown
      await input.trigger("focus");
      await input.setValue("Different");
      const optionButtons = wrapper.findAll('[data-testid="option"]');
      await optionButtons[0].trigger("mousedown");

      expect(wrapper.find('[data-testid="suggestion-panel"]').exists()).toBe(false);
    });

    it("dismisses conflict panel when dismiss button clicked", async () => {
      const createFn = vi.fn().mockRejectedValue({
        response: {
          status: 409,
          data: {
            error: "similar_entity_exists",
            entity_type: "author",
            input: "Test",
            suggestions: [{ id: 1, name: "Similar", match: 0.8, book_count: 0 }],
            resolution: "Use existing",
          },
        },
      });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Test");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="suggestion-panel"]').exists()).toBe(true);

      const dismissButton = wrapper.find('[data-testid="dismiss-conflict"]');
      await dismissButton.trigger("click");

      expect(wrapper.find('[data-testid="suggestion-panel"]').exists()).toBe(false);
    });

    it("handles empty suggestions array gracefully", async () => {
      const createFn = vi.fn().mockRejectedValue({
        response: {
          status: 409,
          data: {
            error: "similar_entity_exists",
            entity_type: "author",
            input: "BadName",
            suggestions: [],
            resolution: "Try different name",
          },
        },
      });

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("BadName");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      // Should show panel with fallback message
      expect(wrapper.find('[data-testid="suggestion-panel"]').exists()).toBe(true);
      expect(wrapper.text()).toContain("could not be created");
      expect(wrapper.text()).toContain("BadName");
      // Should NOT show "create anyway" when no suggestions
      expect(wrapper.find('[data-testid="create-anyway"]').exists()).toBe(false);
    });

    it("emits error event for non-409 errors", async () => {
      const networkError = new Error("Network failed");
      const createFn = vi.fn().mockRejectedValue(networkError);

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Test");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted("error")).toBeTruthy();
      expect(wrapper.emitted("error")![0]).toEqual([networkError]);
      // Should NOT show conflict panel for non-409 errors
      expect(wrapper.find('[data-testid="suggestion-panel"]').exists()).toBe(false);
    });

    it("emits error event for 500 errors", async () => {
      const serverError = {
        response: { status: 500, data: { detail: "Internal error" } },
      };
      const createFn = vi.fn().mockRejectedValue(serverError);

      const wrapper = mount(ComboboxWithAdd, {
        props: {
          label: "Author",
          options: [],
          modelValue: null,
          createFn,
        },
      });

      const input = wrapper.find("input");
      await input.setValue("Test");
      const addButton = wrapper.find('[data-testid="add-new"]');
      await addButton.trigger("mousedown");
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted("error")).toBeTruthy();
      expect(wrapper.emitted("error")![0]).toEqual([serverError]);
    });
  });
});
