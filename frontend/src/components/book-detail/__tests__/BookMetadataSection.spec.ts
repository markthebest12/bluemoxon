import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import BookMetadataSection from "../BookMetadataSection.vue";
import type { Book } from "@/stores/books";

describe("BookMetadataSection", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  // Factory function for creating book props
  function createBook(overrides: Partial<Book> = {}): Book {
    return {
      id: 1,
      title: "Test Book",
      author: { id: 1, name: "Test Author" },
      publisher: { id: 1, name: "Test Publisher", tier: "Tier 1" },
      binder: { id: 1, name: "Test Bindery" },
      publication_date: "1850",
      edition: "First Edition",
      volumes: 2,
      category: "Literature",
      inventory_type: "RARE",
      binding_type: "Full Leather",
      binding_authenticated: false,
      binding_description: null,
      condition_grade: "VG",
      condition_notes: null,
      value_low: 100,
      value_mid: 150,
      value_high: 200,
      purchase_price: 80,
      acquisition_cost: 90,
      purchase_date: "2024-01-15",
      purchase_source: "Auction",
      discount_pct: 20,
      roi_pct: 50,
      status: "ON_HAND",
      notes: null,
      provenance: null,
      is_first_edition: false,
      has_provenance: false,
      provenance_tier: null,
      has_analysis: false,
      has_eval_runbook: false,
      image_count: 0,
      primary_image_url: null,
      investment_grade: null,
      strategic_fit: null,
      collection_impact: null,
      overall_score: null,
      scores_calculated_at: null,
      source_url: null,
      source_item_id: null,
      estimated_delivery: null,
      source_archived_url: null,
      archive_status: null,
      ...overrides,
    };
  }

  describe("Publication Details Card", () => {
    it("renders publisher name and tier", () => {
      const book = createBook({
        publisher: { id: 1, name: "Macmillan", tier: "Tier 1" },
      });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Macmillan");
      expect(wrapper.text()).toContain("Tier 1");
    });

    it("shows '1st Edition' badge when is_first_edition is true", () => {
      const book = createBook({ is_first_edition: true });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("1st Edition");
    });

    it("does not show '1st Edition' badge when is_first_edition is false", () => {
      const book = createBook({ is_first_edition: false });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).not.toContain("1st Edition");
    });

    it("shows Tier 1 provenance badge", () => {
      const book = createBook({ has_provenance: true, provenance_tier: "Tier 1" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Tier 1 Provenance");
    });

    it("shows Tier 2 provenance badge", () => {
      const book = createBook({ has_provenance: true, provenance_tier: "Tier 2" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Tier 2 Provenance");
    });

    it("shows Tier 3 provenance badge", () => {
      const book = createBook({ has_provenance: true, provenance_tier: "Tier 3" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Tier 3 Provenance");
    });

    it("shows 'Has Provenance' badge when has_provenance is true but no tier", () => {
      const book = createBook({ has_provenance: true, provenance_tier: null });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Has Provenance");
    });

    it("displays publication date", () => {
      const book = createBook({ publication_date: "1875" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("1875");
    });

    it("displays edition", () => {
      const book = createBook({ edition: "Second Edition" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Second Edition");
    });

    it("displays volumes", () => {
      const book = createBook({ volumes: 3 });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("3");
    });

    it("displays category", () => {
      const book = createBook({ category: "Poetry" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Poetry");
    });
  });

  describe("Status display and editing", () => {
    it("shows status dropdown for editors", () => {
      const book = createBook({ status: "ON_HAND" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: true },
      });

      const select = wrapper.find("select");
      expect(select.exists()).toBe(true);
    });

    it("emits 'status-changed' when status dropdown changes", async () => {
      const book = createBook({ status: "ON_HAND" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: true },
      });

      const select = wrapper.find("select");
      await select.setValue("EVALUATING");

      expect(wrapper.emitted("status-changed")).toBeTruthy();
      expect(wrapper.emitted("status-changed")![0]).toEqual(["EVALUATING"]);
    });

    it("shows read-only status badge for non-editors", () => {
      const book = createBook({ status: "ON_HAND" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      const select = wrapper.find("select");
      expect(select.exists()).toBe(false);
      // Should have badge with status text
      expect(wrapper.text()).toContain("ON HAND");
    });

    it("displays correct status label for EVALUATING", () => {
      const book = createBook({ status: "EVALUATING" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("EVAL");
    });

    it("displays correct status label for IN_TRANSIT", () => {
      const book = createBook({ status: "IN_TRANSIT" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("IN TRANSIT");
    });
  });

  describe("Binding Card", () => {
    it("renders binding type", () => {
      const book = createBook({ binding_type: "Half Calf" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Half Calf");
    });

    it("shows bindery name when binding_authenticated is true", () => {
      const book = createBook({
        binding_authenticated: true,
        binder: { id: 1, name: "Riviere" },
      });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Riviere");
      expect(wrapper.text()).toContain("Authenticated");
    });

    it("does not show bindery when binding_authenticated is false", () => {
      const book = createBook({
        binding_authenticated: false,
        binder: { id: 1, name: "Riviere" },
      });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      // Should not show bindery section
      const text = wrapper.text();
      // The binding type section should exist, but not the authenticated bindery
      expect(text).not.toContain("Riviere");
    });

    it("shows binding description when present", () => {
      const book = createBook({
        binding_description: "Gilt spine with raised bands",
      });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Gilt spine with raised bands");
    });

    it("does not show binding description section when empty", () => {
      const book = createBook({ binding_description: null });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      // Look for the Description label in binding card - it should not exist
      const ddElements = wrapper.findAll("dd");
      const descriptionExists = ddElements.some((el) => el.text().includes("Gilt spine"));
      expect(descriptionExists).toBe(false);
    });
  });

  describe("Notes Card", () => {
    it("shows notes card only when notes exists", () => {
      const book = createBook({ notes: "Important inscription on endpaper" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      expect(wrapper.text()).toContain("Notes");
      expect(wrapper.text()).toContain("Important inscription on endpaper");
    });

    it("does not show notes card when notes is null", () => {
      const book = createBook({ notes: null });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      // The Notes heading should not appear
      const headings = wrapper.findAll("h2");
      const hasNotesHeading = headings.some((h) => h.text() === "Notes");
      expect(hasNotesHeading).toBe(false);
    });

    it("does not show notes card when notes is empty string", () => {
      const book = createBook({ notes: "" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: false },
      });

      const headings = wrapper.findAll("h2");
      const hasNotesHeading = headings.some((h) => h.text() === "Notes");
      expect(hasNotesHeading).toBe(false);
    });
  });

  describe("updatingStatus state", () => {
    it("disables dropdown when updatingStatus prop is true", () => {
      const book = createBook({ status: "ON_HAND" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: true, updatingStatus: true },
      });

      const select = wrapper.find("select");
      expect(select.attributes("disabled")).toBeDefined();
    });

    it("enables dropdown when updatingStatus prop is false", () => {
      const book = createBook({ status: "ON_HAND" });
      const wrapper = mount(BookMetadataSection, {
        props: { book, isEditor: true, updatingStatus: false },
      });

      const select = wrapper.find("select");
      expect(select.attributes("disabled")).toBeUndefined();
    });
  });
});
