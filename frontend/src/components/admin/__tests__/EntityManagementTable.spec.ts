import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import EntityManagementTable from "../EntityManagementTable.vue";

const mockEntities = [
  { id: 1, name: "Author One", tier: "TIER_1", preferred: true, book_count: 5 },
  { id: 2, name: "Author Two", tier: null, preferred: false, book_count: 3 },
  { id: 3, name: "Author Three", tier: "TIER_2", preferred: false, book_count: 0 },
];

describe("EntityManagementTable", () => {
  describe("per-row loading indicator (#666)", () => {
    it("shows loading spinner for rows with saving IDs", () => {
      const wrapper = mount(EntityManagementTable, {
        props: {
          entityType: "author",
          entities: mockEntities,
          loading: false,
          canEdit: true,
          searchQuery: "",
          savingIds: new Set(["author-1"]),
        },
      });

      // Find the row for entity id=1
      const rows = wrapper.findAll("tbody tr");
      const row1 = rows[0];

      // Should have a loading indicator
      expect(row1.find('[data-testid="saving-spinner"]').exists()).toBe(true);

      // Other rows should not have loading indicator
      const row2 = rows[1];
      expect(row2.find('[data-testid="saving-spinner"]').exists()).toBe(false);
    });

    it("disables tier select for rows being saved", () => {
      const wrapper = mount(EntityManagementTable, {
        props: {
          entityType: "author",
          entities: mockEntities,
          loading: false,
          canEdit: true,
          searchQuery: "",
          savingIds: new Set(["author-1"]),
        },
      });

      const rows = wrapper.findAll("tbody tr");
      const row1TierSelect = rows[0].find("select");
      const row2TierSelect = rows[1].find("select");

      expect(row1TierSelect.attributes("disabled")).toBeDefined();
      expect(row2TierSelect.attributes("disabled")).toBeUndefined();
    });

    it("disables preferred checkbox for rows being saved", () => {
      // Note: entities are sorted by component (preferred first, then tier, then name)
      // So order is: Author One (id:1), Author Three (id:3), Author Two (id:2)
      const wrapper = mount(EntityManagementTable, {
        props: {
          entityType: "author",
          entities: mockEntities,
          loading: false,
          canEdit: true,
          searchQuery: "",
          savingIds: new Set(["author-3"]), // Author Three is at index 1 after sorting
        },
      });

      const rows = wrapper.findAll("tbody tr");
      const row0Checkbox = rows[0].find('input[type="checkbox"]'); // Author One
      const row1Checkbox = rows[1].find('input[type="checkbox"]'); // Author Three (saving)

      // Row 0 should NOT be disabled (not in savingIds)
      expect(row0Checkbox.attributes("disabled")).toBeUndefined();
      // Row 1 (Author Three) should be disabled (in savingIds)
      expect(row1Checkbox.attributes("disabled")).toBeDefined();
    });

    it("accepts empty savingIds set gracefully", () => {
      const wrapper = mount(EntityManagementTable, {
        props: {
          entityType: "author",
          entities: mockEntities,
          loading: false,
          canEdit: true,
          searchQuery: "",
          savingIds: new Set<string>(),
        },
      });

      // Should render without errors
      expect(wrapper.findAll("tbody tr")).toHaveLength(3);
      // No spinners should be visible
      expect(wrapper.findAll('[data-testid="saving-spinner"]')).toHaveLength(0);
    });
  });

  describe("existing functionality", () => {
    it("emits update:tier when tier select changes", async () => {
      const wrapper = mount(EntityManagementTable, {
        props: {
          entityType: "author",
          entities: mockEntities,
          loading: false,
          canEdit: true,
          searchQuery: "",
          savingIds: new Set<string>(),
        },
      });

      const select = wrapper.find("select");
      await select.setValue("TIER_2");

      expect(wrapper.emitted("update:tier")).toBeTruthy();
      expect(wrapper.emitted("update:tier")![0]).toEqual([1, "TIER_2"]);
    });

    it("emits update:preferred when checkbox changes", async () => {
      const wrapper = mount(EntityManagementTable, {
        props: {
          entityType: "author",
          entities: mockEntities,
          loading: false,
          canEdit: true,
          searchQuery: "",
          savingIds: new Set<string>(),
        },
      });

      const checkbox = wrapper.find('input[type="checkbox"]');
      await checkbox.setValue(false);

      expect(wrapper.emitted("update:preferred")).toBeTruthy();
      expect(wrapper.emitted("update:preferred")![0]).toEqual([1, false]);
    });

    it("filters entities by search query", () => {
      const wrapper = mount(EntityManagementTable, {
        props: {
          entityType: "author",
          entities: mockEntities,
          loading: false,
          canEdit: true,
          searchQuery: "Two",
          savingIds: new Set<string>(),
        },
      });

      const rows = wrapper.findAll("tbody tr");
      expect(rows).toHaveLength(1);
      expect(rows[0].text()).toContain("Author Two");
    });
  });
});
