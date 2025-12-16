import { describe, it, expect } from "vitest";
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
});
