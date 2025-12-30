import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import EntityFormModal from "../EntityFormModal.vue";

// Mock TransitionModal to avoid portal/teleport issues
vi.mock("@/components/TransitionModal.vue", () => ({
  default: {
    name: "TransitionModal",
    template: '<div v-if="visible"><slot /></div>',
    props: ["visible"],
  },
}));

describe("EntityFormModal", () => {
  describe("form validation (#664)", () => {
    describe("name validation (all entity types)", () => {
      it("shows error when name exceeds 255 characters", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "author",
            entity: null,
            saving: false,
            error: null,
          },
        });

        const nameInput = wrapper.find('input[type="text"]');
        await nameInput.setValue("a".repeat(256));

        // Trigger validation by clicking submit (Save button)
        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1]; // Last button is Save
        await submitButton.trigger("click");

        // Should show validation error
        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="validation-error"]').text()).toContain(
          "Name must be 255 characters or less"
        );
      });

      it("does not emit save when name exceeds 255 characters", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "author",
            entity: null,
            saving: false,
            error: null,
          },
        });

        const nameInput = wrapper.find('input[type="text"]');
        await nameInput.setValue("a".repeat(256));

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.emitted("save")).toBeFalsy();
      });

      it("allows name of exactly 255 characters", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "author",
            entity: null,
            saving: false,
            error: null,
          },
        });

        const nameInput = wrapper.find('input[type="text"]');
        await nameInput.setValue("a".repeat(255));

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.emitted("save")).toBeTruthy();
      });
    });

    describe("author year validation", () => {
      it("shows error when birth_year is after death_year", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "author",
            entity: null,
            saving: false,
            error: null,
          },
        });

        await wrapper.find('input[type="text"]').setValue("Test Author");
        const numberInputs = wrapper.findAll('input[type="number"]');
        await numberInputs[0].setValue(1900); // birth_year
        await numberInputs[1].setValue(1850); // death_year

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="validation-error"]').text()).toContain(
          "Birth year must be before death year"
        );
      });

      it("shows error when birth_year is below 1000", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "author",
            entity: null,
            saving: false,
            error: null,
          },
        });

        await wrapper.find('input[type="text"]').setValue("Test Author");
        const numberInputs = wrapper.findAll('input[type="number"]');
        await numberInputs[0].setValue(999); // birth_year

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="validation-error"]').text()).toContain(
          "Year must be between 1000 and 2100"
        );
      });

      it("shows error when death_year exceeds 2100", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "author",
            entity: null,
            saving: false,
            error: null,
          },
        });

        await wrapper.find('input[type="text"]').setValue("Test Author");
        const numberInputs = wrapper.findAll('input[type="number"]');
        await numberInputs[1].setValue(2101); // death_year

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="validation-error"]').text()).toContain(
          "Year must be between 1000 and 2100"
        );
      });

      it("allows valid author years", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "author",
            entity: null,
            saving: false,
            error: null,
          },
        });

        await wrapper.find('input[type="text"]').setValue("Test Author");
        const numberInputs = wrapper.findAll('input[type="number"]');
        await numberInputs[0].setValue(1800); // birth_year
        await numberInputs[1].setValue(1870); // death_year

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.emitted("save")).toBeTruthy();
        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(false);
      });
    });

    describe("publisher year validation", () => {
      it("shows error when founded_year is below 1000", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "publisher",
            entity: null,
            saving: false,
            error: null,
          },
        });

        await wrapper.find('input[type="text"]').setValue("Test Publisher");
        const foundedInput = wrapper.find('input[type="number"]');
        await foundedInput.setValue(999);

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="validation-error"]').text()).toContain(
          "Founded year must be between 1000"
        );
      });

      it("shows error when founded_year is in the future", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "publisher",
            entity: null,
            saving: false,
            error: null,
          },
        });

        await wrapper.find('input[type="text"]').setValue("Test Publisher");
        const foundedInput = wrapper.find('input[type="number"]');
        const futureYear = new Date().getFullYear() + 1;
        await foundedInput.setValue(futureYear);

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="validation-error"]').text()).toContain(
          "Founded year must be between 1000"
        );
      });

      it("allows valid publisher founded year", async () => {
        const wrapper = mount(EntityFormModal, {
          props: {
            visible: true,
            entityType: "publisher",
            entity: null,
            saving: false,
            error: null,
          },
        });

        await wrapper.find('input[type="text"]').setValue("Test Publisher");
        const foundedInput = wrapper.find('input[type="number"]');
        await foundedInput.setValue(1920);

        const buttons = wrapper.findAll("button");
        const submitButton = buttons[buttons.length - 1];
        await submitButton.trigger("click");

        expect(wrapper.emitted("save")).toBeTruthy();
        expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(false);
      });
    });
  });
});
