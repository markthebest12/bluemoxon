import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookSidebarSection from "../BookSidebarSection.vue";
import type { Book } from "@/stores/books";

// Helper to create a minimal Book object for testing
function createTestBook(overrides: Partial<Book> = {}): Book {
  return {
    id: 1,
    title: "Test Book",
    author: null,
    publisher: null,
    binder: null,
    publication_date: null,
    edition: null,
    volumes: 1,
    category: null,
    inventory_type: "collection",
    binding_type: null,
    binding_authenticated: false,
    binding_description: null,
    condition_grade: null,
    condition_notes: null,
    value_low: null,
    value_mid: null,
    value_high: null,
    purchase_price: null,
    acquisition_cost: null,
    purchase_date: null,
    purchase_source: null,
    discount_pct: null,
    roi_pct: null,
    status: "owned",
    notes: null,
    provenance: null,
    is_first_edition: null,
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

describe("BookSidebarSection", () => {
  describe("Valuation Card", () => {
    it("renders valuation with mid/low/high estimates", () => {
      const book = createTestBook({
        value_low: 500,
        value_mid: 750,
        value_high: 1000,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      // Check mid estimate (large, gold text)
      expect(wrapper.text()).toContain("$750");
      expect(wrapper.text()).toContain("Mid Estimate");

      // Check low/high estimates
      expect(wrapper.text()).toContain("$500");
      expect(wrapper.text()).toContain("Low");
      expect(wrapper.text()).toContain("$1,000");
      expect(wrapper.text()).toContain("High");
    });

    it("shows purchase price in valuation when present", () => {
      const book = createTestBook({
        value_mid: 750,
        value_low: 500,
        value_high: 1000,
        purchase_price: 400,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("$400");
      expect(wrapper.text()).toContain("Purchase Price");
    });

    it("does not show purchase price section when not present", () => {
      const book = createTestBook({
        value_mid: 750,
        value_low: 500,
        value_high: 1000,
        purchase_price: null,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      // The valuation card should exist but no purchase price section
      const valuationCard = wrapper.find(".bg-victorian-cream");
      expect(valuationCard.exists()).toBe(true);
      expect(valuationCard.text()).not.toContain("Purchase Price");
    });
  });

  describe("Acquisition Card", () => {
    it("shows acquisition card only when purchase_price exists", () => {
      const bookWithPurchase = createTestBook({
        purchase_price: 400,
      });

      const bookWithoutPurchase = createTestBook({
        purchase_price: null,
      });

      const wrapperWith = mount(BookSidebarSection, {
        props: { book: bookWithPurchase, imageCount: 0 },
      });

      const wrapperWithout = mount(BookSidebarSection, {
        props: { book: bookWithoutPurchase, imageCount: 0 },
      });

      expect(wrapperWith.text()).toContain("Acquisition");
      expect(wrapperWithout.text()).not.toContain("Acquisition");
    });

    it("shows acquisition cost when present", () => {
      const book = createTestBook({
        purchase_price: 400,
        acquisition_cost: 450,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("$450");
      expect(wrapper.text()).toContain("Acquisition Cost");
      expect(wrapper.text()).toContain("(incl. shipping/tax)");
    });

    it("shows discount_pct when present", () => {
      const book = createTestBook({
        purchase_price: 400,
        discount_pct: 25,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("Discount");
      expect(wrapper.text()).toContain("25%");
    });

    it("shows roi_pct when present", () => {
      const book = createTestBook({
        purchase_price: 400,
        roi_pct: 87.5,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("ROI");
      expect(wrapper.text()).toContain("87.5%");
    });
  });

  describe("Source Archive Card", () => {
    it("shows source archive section only when source_url exists", () => {
      const bookWithSource = createTestBook({
        source_url: "https://ebay.com/item/123",
      });

      const bookWithoutSource = createTestBook({
        source_url: null,
      });

      const wrapperWith = mount(BookSidebarSection, {
        props: { book: bookWithSource, imageCount: 0 },
      });

      const wrapperWithout = mount(BookSidebarSection, {
        props: { book: bookWithoutSource, imageCount: 0 },
      });

      expect(wrapperWith.text()).toContain("Source Archive");
      expect(wrapperWith.text()).toContain("Original Listing");
      expect(wrapperWithout.text()).not.toContain("Source Archive");
    });

    it("renders source link with correct href", () => {
      const book = createTestBook({
        source_url: "https://ebay.com/item/123",
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      const sourceLink = wrapper.find('a[href="https://ebay.com/item/123"]');
      expect(sourceLink.exists()).toBe(true);
      expect(sourceLink.text()).toBe("View Source");
      expect(sourceLink.attributes("target")).toBe("_blank");
      expect(sourceLink.attributes("rel")).toBe("noopener noreferrer");
    });

    it("displays archive status badge when source present", () => {
      const book = createTestBook({
        source_url: "https://ebay.com/item/123",
        archive_status: "success",
        source_archived_url: "https://archive.org/web/123",
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("Archive Status");
      // ArchiveStatusBadge should render "Archived" for success status
      expect(wrapper.text()).toContain("Archived");
    });
  });

  describe("Quick Info Card", () => {
    it("shows correct image count from prop", () => {
      const book = createTestBook();

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 5 },
      });

      expect(wrapper.text()).toContain("Images");
      expect(wrapper.text()).toContain("5");
    });

    it('shows "Yes" for has_analysis when true', () => {
      const book = createTestBook({
        has_analysis: true,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("Has Analysis");
      expect(wrapper.text()).toContain("Yes");
    });

    it('shows "No" for has_analysis when false', () => {
      const book = createTestBook({
        has_analysis: false,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("Has Analysis");
      expect(wrapper.text()).toContain("No");
    });

    it("shows inventory type", () => {
      const book = createTestBook({
        inventory_type: "wishlist",
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("Inventory Type");
      expect(wrapper.text()).toContain("wishlist");
    });
  });

  describe("Currency Formatting", () => {
    it("formats currency values with commas for thousands", () => {
      const book = createTestBook({
        value_mid: 12500,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      expect(wrapper.text()).toContain("$12,500");
    });

    it('shows "-" for null currency values', () => {
      const book = createTestBook({
        value_mid: null,
        value_low: null,
        value_high: null,
      });

      const wrapper = mount(BookSidebarSection, {
        props: { book, imageCount: 0 },
      });

      // The mid estimate should show "-"
      const midEstimate = wrapper.find(".text-3xl");
      expect(midEstimate.text()).toBe("-");
    });
  });
});
