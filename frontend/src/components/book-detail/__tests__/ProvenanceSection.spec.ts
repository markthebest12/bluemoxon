import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ProvenanceSection from "../ProvenanceSection.vue";

describe("ProvenanceSection", () => {
  const defaultProps = {
    bookId: 123,
    provenance: "This book was owned by John Smith in 1850.",
    isEditor: true,
  };

  it("renders provenance text when present", () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    expect(wrapper.text()).toContain("This book was owned by John Smith in 1850.");
  });

  it('shows "No provenance" message when provenance is null', () => {
    const wrapper = mount(ProvenanceSection, {
      props: {
        ...defaultProps,
        provenance: null,
      },
    });

    expect(wrapper.text()).toContain("No provenance information");
  });

  it('shows "No provenance" message when provenance is empty string', () => {
    const wrapper = mount(ProvenanceSection, {
      props: {
        ...defaultProps,
        provenance: "",
      },
    });

    expect(wrapper.text()).toContain("No provenance information");
  });

  it('shows "Edit" button for editors when provenance exists', () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    const editButton = wrapper.find("button");
    expect(editButton.exists()).toBe(true);
    expect(editButton.text()).toBe("Edit");
  });

  it('shows "Add provenance" button for editors when no provenance', () => {
    const wrapper = mount(ProvenanceSection, {
      props: {
        ...defaultProps,
        provenance: null,
      },
    });

    const addButton = wrapper.find("button");
    expect(addButton.exists()).toBe(true);
    expect(addButton.text()).toBe("Add provenance");
  });

  it("hides edit button for non-editors", () => {
    const wrapper = mount(ProvenanceSection, {
      props: {
        ...defaultProps,
        isEditor: false,
      },
    });

    // Should not find any button in the header area
    const buttons = wrapper.findAll("button");
    expect(buttons.length).toBe(0);
  });

  it("clicking edit button shows textarea with provenance text", async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Initially no textarea
    expect(wrapper.find("textarea").exists()).toBe(false);

    // Click edit
    await wrapper.find("button").trigger("click");

    // Now textarea should be visible with provenance text
    const textarea = wrapper.find("textarea");
    expect(textarea.exists()).toBe(true);
    expect((textarea.element as HTMLTextAreaElement).value).toBe(
      "This book was owned by John Smith in 1850."
    );
  });

  it("cancel button resets and hides textarea", async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Enter edit mode
    await wrapper.find("button").trigger("click");
    expect(wrapper.find("textarea").exists()).toBe(true);

    // Modify text
    await wrapper.find("textarea").setValue("Modified text");

    // Find and click cancel button
    const buttons = wrapper.findAll("button");
    const cancelButton = buttons.find((btn) => btn.text() === "Cancel");
    expect(cancelButton).toBeDefined();
    await cancelButton!.trigger("click");

    // Textarea should be hidden
    expect(wrapper.find("textarea").exists()).toBe(false);

    // Re-enter edit mode - should have original text, not modified
    await wrapper.find("button").trigger("click");
    expect((wrapper.find("textarea").element as HTMLTextAreaElement).value).toBe(
      "This book was owned by John Smith in 1850."
    );
  });

  it('save button emits "provenance-saved" with new text', async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Enter edit mode
    await wrapper.find("button").trigger("click");

    // Modify text
    await wrapper.find("textarea").setValue("New provenance text");

    // Find and click save button
    const buttons = wrapper.findAll("button");
    const saveButton = buttons.find((btn) => btn.text() === "Save");
    expect(saveButton).toBeDefined();
    await saveButton!.trigger("click");

    // Check emitted event
    const emitted = wrapper.emitted("provenance-saved");
    expect(emitted).toBeTruthy();
    expect(emitted![0]).toEqual(["New provenance text"]);
  });

  it('save button shows "Saving..." while waiting for parent callback', async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Enter edit mode
    await wrapper.find("button").trigger("click");

    // Find save button before clicking
    let buttons = wrapper.findAll("button");
    const saveButton = buttons.find((btn) => btn.text() === "Save");
    expect(saveButton).toBeDefined();

    // Click save - it should show "Saving..." and stay in that state
    await saveButton!.trigger("click");

    // Verify emit happened
    expect(wrapper.emitted("provenance-saved")).toBeTruthy();

    // Button should show "Saving..." while waiting for parent callback
    buttons = wrapper.findAll("button");
    const savingButton = buttons.find((btn) => btn.text() === "Saving...");
    expect(savingButton).toBeDefined();
    expect(savingButton!.attributes("disabled")).toBeDefined();
  });

  it("empty text emits null for provenance-saved", async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Enter edit mode
    await wrapper.find("button").trigger("click");

    // Clear the text
    await wrapper.find("textarea").setValue("");

    // Find and click save button
    const buttons = wrapper.findAll("button");
    const saveButton = buttons.find((btn) => btn.text() === "Save");
    await saveButton!.trigger("click");

    // Check emitted event - should be null for empty text
    const emitted = wrapper.emitted("provenance-saved");
    expect(emitted).toBeTruthy();
    expect(emitted![0]).toEqual([null]);
  });

  it("whitespace-only text emits null for provenance-saved", async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Enter edit mode
    await wrapper.find("button").trigger("click");

    // Set whitespace-only text
    await wrapper.find("textarea").setValue("   \n  ");

    // Find and click save button
    const buttons = wrapper.findAll("button");
    const saveButton = buttons.find((btn) => btn.text() === "Save");
    await saveButton!.trigger("click");

    // Check emitted event - should be null for whitespace-only
    const emitted = wrapper.emitted("provenance-saved");
    expect(emitted).toBeTruthy();
    expect(emitted![0]).toEqual([null]);
  });

  it("closes edit mode only after parent calls onSaveSuccess", async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Enter edit mode
    await wrapper.find("button").trigger("click");
    expect(wrapper.find("textarea").exists()).toBe(true);

    // Save - edit mode should NOT close yet
    const buttons = wrapper.findAll("button");
    const saveButton = buttons.find((btn) => btn.text() === "Save");
    await saveButton!.trigger("click");

    // Edit mode should still be open (waiting for parent callback)
    expect(wrapper.find("textarea").exists()).toBe(true);

    // Parent calls onSaveSuccess
    wrapper.vm.onSaveSuccess();
    await wrapper.vm.$nextTick();

    // Now edit mode should be closed
    expect(wrapper.find("textarea").exists()).toBe(false);
  });

  it("keeps edit mode open when parent calls onSaveError", async () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    // Enter edit mode
    await wrapper.find("button").trigger("click");
    expect(wrapper.find("textarea").exists()).toBe(true);

    // Save
    const buttons = wrapper.findAll("button");
    const saveButton = buttons.find((btn) => btn.text() === "Save");
    await saveButton!.trigger("click");

    // Parent calls onSaveError
    wrapper.vm.onSaveError();
    await wrapper.vm.$nextTick();

    // Edit mode should still be open for retry
    expect(wrapper.find("textarea").exists()).toBe(true);

    // But save button should be enabled again (not showing "Saving...")
    const retryButtons = wrapper.findAll("button");
    const retrySaveButton = retryButtons.find((btn) => btn.text() === "Save");
    expect(retrySaveButton).toBeDefined();
  });

  it("renders the Provenance heading", () => {
    const wrapper = mount(ProvenanceSection, {
      props: defaultProps,
    });

    expect(wrapper.find("h2").text()).toBe("Provenance");
  });
});
