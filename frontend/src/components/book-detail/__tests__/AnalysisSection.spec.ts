import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { ref } from "vue";
import AnalysisSection from "../AnalysisSection.vue";
import type { Book } from "@/stores/books";

// Create a mock function we can control
const mockUseJobPolling = vi.fn();

// Mock stores and composables
vi.mock("@/stores/books", () => ({
  useBooksStore: vi.fn(() => ({
    generateAnalysisAsync: vi.fn(),
  })),
}));

vi.mock("@/composables/useJobPolling", () => ({
  useJobPolling: (...args: unknown[]) => mockUseJobPolling(...args),
}));

// Stub child components
const stubs = {
  AnalysisViewer: true,
  EvalRunbookModal: true,
  AnalysisIssuesWarning: {
    template: '<span data-testid="analysis-issues-warning"><slot /></span>',
    props: ["issues"],
  },
};

describe("AnalysisSection", () => {
  const createBook = (overrides: Partial<Book> = {}): Book => ({
    id: 123,
    title: "Test Book",
    author: null,
    publisher: null,
    binder: null,
    publication_date: null,
    year_start: null,
    year_end: null,
    edition: null,
    volumes: 1,
    is_complete: true,
    category: null,
    inventory_type: "collected",
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
    status: "collected",
    notes: null,
    provenance: null,
    is_first_edition: null,
    has_provenance: false,
    provenance_tier: null,
    has_analysis: false,
    has_eval_runbook: false,
    analysis_job_status: undefined,
    eval_runbook_job_status: undefined,
    analysis_issues: null,
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
    estimated_delivery_end: null,
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    tracking_status: null,
    tracking_last_checked: null,
    ship_date: null,
    source_archived_url: null,
    archive_status: null,
    created_at: "2024-01-01T00:00:00Z",
    ...overrides,
  });

  const defaultProps = {
    book: createBook(),
    isEditor: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the mock to return default values
    mockUseJobPolling.mockReturnValue({
      start: vi.fn(),
      stop: vi.fn(),
      isActive: ref(false),
      status: ref(null),
      error: ref(null),
      pollInterval: 5000,
    });
  });

  describe("Eval Runbook card", () => {
    it("shows Eval Runbook card when has_eval_runbook is true", () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ has_eval_runbook: true }),
        },
        global: { stubs },
      });

      expect(wrapper.text()).toContain("Eval Runbook");
      expect(wrapper.text()).toContain("View Runbook");
    });

    it("hides Eval Runbook card when has_eval_runbook is false", () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ has_eval_runbook: false }),
        },
        global: { stubs },
      });

      expect(wrapper.text()).not.toContain("View Runbook");
    });
  });

  describe("Analysis card - View Analysis button", () => {
    it('shows "View Analysis" button when has_analysis is true', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ has_analysis: true }),
        },
        global: { stubs },
      });

      const buttons = wrapper.findAll("button");
      const viewButton = buttons.find((btn) => btn.text().includes("View Analysis"));
      expect(viewButton).toBeDefined();
    });

    it('hides "View Analysis" button when has_analysis is false', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ has_analysis: false }),
        },
        global: { stubs },
      });

      const buttons = wrapper.findAll("button");
      const viewButton = buttons.find((btn) => btn.text().includes("View Analysis"));
      expect(viewButton).toBeUndefined();
    });
  });

  describe("Analysis card - Generate Analysis button", () => {
    it('shows "Generate Analysis" button for editors when no analysis', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: false }),
          isEditor: true,
        },
        global: { stubs },
      });

      const buttons = wrapper.findAll("button");
      const generateButton = buttons.find((btn) => btn.text().includes("Generate Analysis"));
      expect(generateButton).toBeDefined();
    });

    it('hides "Generate Analysis" button for non-editors', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: false }),
          isEditor: false,
        },
        global: { stubs },
      });

      const buttons = wrapper.findAll("button");
      const generateButton = buttons.find((btn) => btn.text().includes("Generate Analysis"));
      expect(generateButton).toBeUndefined();
    });
  });

  describe("Analysis card - Regenerate button", () => {
    it('shows "Regenerate" button for editors when has_analysis is true', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: true }),
          isEditor: true,
        },
        global: { stubs },
      });

      const buttons = wrapper.findAll("button");
      const regenerateButton = buttons.find((btn) => btn.text().includes("Regenerate"));
      expect(regenerateButton).toBeDefined();
    });

    it('hides "Regenerate" button for non-editors', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: true }),
          isEditor: false,
        },
        global: { stubs },
      });

      const buttons = wrapper.findAll("button");
      const regenerateButton = buttons.find((btn) => btn.text().includes("Regenerate"));
      expect(regenerateButton).toBeUndefined();
    });
  });

  describe("Analysis card - Model selector", () => {
    it("shows model selector dropdown for editors", () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: false }),
          isEditor: true,
        },
        global: { stubs },
      });

      const select = wrapper.find("select");
      expect(select.exists()).toBe(true);
    });

    it("hides model selector dropdown for non-editors", () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: false }),
          isEditor: false,
        },
        global: { stubs },
      });

      const select = wrapper.find("select");
      expect(select.exists()).toBe(false);
    });
  });

  describe("Analysis card - Job status messages", () => {
    it('shows "Analyzing..." when analysis_job_status is "running"', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ analysis_job_status: "running" }),
        },
        global: { stubs },
      });

      expect(wrapper.text()).toContain("Analyzing...");
    });

    it('shows "Queued..." when analysis_job_status is "pending"', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ analysis_job_status: "pending" }),
        },
        global: { stubs },
      });

      expect(wrapper.text()).toContain("Queued...");
    });

    it('shows "Analysis failed" message when job status is "failed"', () => {
      // Mock useJobPolling to return failed status
      mockUseJobPolling.mockReturnValue({
        start: vi.fn(),
        stop: vi.fn(),
        isActive: ref(false),
        status: ref("failed"),
        error: ref("Some error"),
        pollInterval: 5000,
      });

      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ has_analysis: false }),
        },
        global: { stubs },
      });

      expect(wrapper.text()).toContain("Analysis failed");
    });
  });

  describe("AnalysisIssuesWarning component", () => {
    it("renders AnalysisIssuesWarning component", () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ has_analysis: true, analysis_issues: ["truncated"] }),
        },
        global: { stubs },
      });

      const warning = wrapper.find('[data-testid="analysis-issues-warning"]');
      expect(warning.exists()).toBe(true);
    });
  });

  describe("Status messages for different states", () => {
    it('shows "View the full Napoleon-style..." when has_analysis is true', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          ...defaultProps,
          book: createBook({ has_analysis: true }),
        },
        global: { stubs },
      });

      expect(wrapper.text()).toContain("View the full Napoleon-style");
    });

    it('shows "Generate a Napoleon-style..." for editors when no analysis', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: false }),
          isEditor: true,
        },
        global: { stubs },
      });

      expect(wrapper.text()).toContain("Generate a Napoleon-style");
    });

    it('shows "No analysis available..." for non-editors when no analysis', () => {
      const wrapper = mount(AnalysisSection, {
        props: {
          book: createBook({ has_analysis: false }),
          isEditor: false,
        },
        global: { stubs },
      });

      expect(wrapper.text()).toContain("No analysis available");
    });
  });

  describe("Detailed Analysis heading", () => {
    it("renders the Detailed Analysis heading", () => {
      const wrapper = mount(AnalysisSection, {
        props: defaultProps,
        global: { stubs },
      });

      expect(wrapper.find("h2").text()).toContain("Detailed Analysis");
    });
  });
});
