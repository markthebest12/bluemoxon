import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import ReassignDeleteModal from "../ReassignDeleteModal.vue";

// Mock TransitionModal
vi.mock("@/components/TransitionModal.vue", () => ({
  default: {
    name: "TransitionModal",
    template: '<div v-if="visible"><slot /></div>',
    props: ["visible"],
  },
}));

const mockEntities = [
  { id: 1, name: "Author One", tier: "TIER_1", preferred: true, book_count: 5 },
  { id: 2, name: "Author Two", tier: null, preferred: false, book_count: 3 },
  { id: 3, name: "Author Three", tier: "TIER_2", preferred: false, book_count: 0 },
];

describe("ReassignDeleteModal", () => {
  describe("target validation (#665)", () => {
    it("excludes self from target options", () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: true,
          entity: mockEntities[0], // Author One (id: 1)
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: null,
        },
      });

      // Should only show Author Two and Author Three as options
      const options = wrapper.findAll("option");
      // First option is the placeholder "Select target author"
      expect(options.length).toBe(3); // placeholder + 2 valid targets
      expect(options[1].text()).toContain("Author Two");
      expect(options[2].text()).toContain("Author Three");
      // Author One should NOT be in the list
      expect(wrapper.text()).not.toContain("Author One (5 books)");
    });

    it("disables delete button when no target selected for entity with books", () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: true,
          entity: mockEntities[0], // Has 5 books
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: null,
        },
      });

      // Find the delete/reassign button (last button in the footer)
      const buttons = wrapper.findAll("button");
      const deleteButton = buttons[buttons.length - 1];
      expect(deleteButton.attributes("disabled")).toBeDefined();
    });

    it("enables delete button when target is selected", async () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: true,
          entity: mockEntities[0], // Has 5 books
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: null,
        },
      });

      // Select a target
      const select = wrapper.find("select");
      await select.setValue(2);

      const buttons = wrapper.findAll("button");
      const deleteButton = buttons[buttons.length - 1];
      expect(deleteButton.attributes("disabled")).toBeUndefined();
    });

    it("displays error message when error prop is set", () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: true,
          entity: mockEntities[0],
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: "Target author not found",
        },
      });

      expect(wrapper.text()).toContain("Target author not found");
    });

    it("resets selection when modal opens", async () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: false,
          entity: mockEntities[0],
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: null,
        },
      });

      // Open modal
      await wrapper.setProps({ visible: true });
      await nextTick();

      // The select shows the placeholder (value is null, displayed as placeholder text)
      // In Vue's v-model with null, the placeholder option with :value="null" is selected
      const select = wrapper.find("select");
      // Check that no valid target is selected (first option is the disabled placeholder)
      expect((select.element as HTMLSelectElement).selectedIndex).toBe(0);
    });

    it("emits reassign-delete with target ID when delete button clicked", async () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: true,
          entity: mockEntities[0], // Has 5 books
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: null,
        },
      });

      // Select a target
      const select = wrapper.find("select");
      await select.setValue(2);

      // Click delete button (last button in the footer)
      const buttons = wrapper.findAll("button");
      const deleteButton = buttons[buttons.length - 1];
      await deleteButton.trigger("click");

      expect(wrapper.emitted("reassign-delete")).toBeTruthy();
      expect(wrapper.emitted("reassign-delete")![0]).toEqual([2]);
    });

    it("resets selection when error occurs", async () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: true,
          entity: mockEntities[0],
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: null,
        },
      });

      // Select a target
      const select = wrapper.find("select");
      await select.setValue(2);
      expect((select.element as HTMLSelectElement).selectedIndex).toBe(1); // First valid option

      // Simulate error being set (from parent component after API failure)
      await wrapper.setProps({ error: "Target author not found" });
      await nextTick();

      // Selection should be reset on error (placeholder option at index 0)
      expect((select.element as HTMLSelectElement).selectedIndex).toBe(0);
    });
  });

  describe("entity without books", () => {
    it("allows direct delete for entities with no books", () => {
      const wrapper = mount(ReassignDeleteModal, {
        props: {
          visible: true,
          entity: mockEntities[2], // Author Three has 0 books
          allEntities: mockEntities,
          entityLabel: "Author",
          processing: false,
          error: null,
        },
      });

      // Should show delete confirmation flow, not reassignment
      expect(wrapper.text()).toContain("no books");
      expect(wrapper.text()).toContain("permanently deleted");
    });
  });
});
