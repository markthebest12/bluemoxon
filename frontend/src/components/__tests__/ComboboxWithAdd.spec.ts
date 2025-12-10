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
});
