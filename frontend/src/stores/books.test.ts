/**
 * Tests for books store - specifically Issue #499 fix
 *
 * Bug: When polling for job status fails (API error), the job stays stuck
 * in the activeAnalysisJobs/activeEvalRunbookJobs Map forever because
 * clearJob() is never called in the error handler.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useBooksStore } from "./books";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/services/api";

describe("books store - job polling error handling", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("startJobPoller error handling", () => {
    it("should clear job from Map when polling fails with API error", async () => {
      const store = useBooksStore();
      const bookId = 123;

      // Set up initial job in the Map (simulating job that was started)
      const mockJob = {
        job_id: "test-job-123",
        book_id: bookId,
        status: "running" as const,
        model: "sonnet",
        error_message: null,
        created_at: "2025-12-21T00:00:00Z",
        updated_at: "2025-12-21T00:00:00Z",
        completed_at: null,
      };

      // Add job to the Map directly (simulating a job that was started)
      store.activeAnalysisJobs = new Map([[bookId, mockJob]]);

      // Verify job is in Map before polling fails
      expect(store.hasActiveJob(bookId)).toBe(true);
      expect(store.getActiveJob(bookId)).toEqual(mockJob);

      // Mock API to fail on status check
      vi.mocked(api.get).mockRejectedValue(new Error("API Error: Job not found"));

      // Start the poller
      store.startJobPoller(bookId, 1000);

      // Fast-forward to trigger the first poll
      await vi.advanceTimersByTimeAsync(1000);

      // BUG: Job should be cleared from Map after polling error
      // Currently this FAILS because clearJob() is not called in catch block
      expect(store.hasActiveJob(bookId)).toBe(false);
      expect(store.getActiveJob(bookId)).toBeUndefined();
    });

    it("should clear job from Map when polling fails multiple times", async () => {
      const store = useBooksStore();
      const bookId = 456;

      // Set up initial running job
      const mockJob = {
        job_id: "test-job-456",
        book_id: bookId,
        status: "pending" as const,
        model: "opus",
        error_message: null,
        created_at: "2025-12-21T00:00:00Z",
        updated_at: "2025-12-21T00:00:00Z",
        completed_at: null,
      };

      store.activeAnalysisJobs = new Map([[bookId, mockJob]]);
      expect(store.hasActiveJob(bookId)).toBe(true);

      // Mock API to fail
      vi.mocked(api.get).mockRejectedValue(new Error("Network error"));

      // Start the poller
      store.startJobPoller(bookId, 500);

      // First poll fails
      await vi.advanceTimersByTimeAsync(500);

      // Job should be cleared after first failure (not left stuck)
      expect(store.hasActiveJob(bookId)).toBe(false);
    });
  });

  describe("startEvalRunbookJobPoller error handling", () => {
    it("should clear eval runbook job from Map when polling fails", async () => {
      const store = useBooksStore();
      const bookId = 789;

      // Set up initial eval runbook job in the Map
      const mockJob = {
        job_id: "eval-job-789",
        book_id: bookId,
        status: "running" as const,
        error_message: null,
        created_at: "2025-12-21T00:00:00Z",
        updated_at: "2025-12-21T00:00:00Z",
        completed_at: null,
      };

      store.activeEvalRunbookJobs = new Map([[bookId, mockJob]]);

      // Verify job is in Map
      expect(store.hasActiveEvalRunbookJob(bookId)).toBe(true);
      expect(store.getActiveEvalRunbookJob(bookId)).toEqual(mockJob);

      // Mock API to fail
      vi.mocked(api.get).mockRejectedValue(new Error("404 Not Found"));

      // Start the poller
      store.startEvalRunbookJobPoller(bookId, 1000);

      // Fast-forward to trigger poll
      await vi.advanceTimersByTimeAsync(1000);

      // BUG: Job should be cleared from Map after polling error
      expect(store.hasActiveEvalRunbookJob(bookId)).toBe(false);
      expect(store.getActiveEvalRunbookJob(bookId)).toBeUndefined();
    });
  });

  describe("successful job completion still works", () => {
    it("should clear job when status is completed", async () => {
      const store = useBooksStore();
      const bookId = 100;

      // Set up running job
      const runningJob = {
        job_id: "test-job-100",
        book_id: bookId,
        status: "running" as const,
        model: "sonnet",
        error_message: null,
        created_at: "2025-12-21T00:00:00Z",
        updated_at: "2025-12-21T00:00:00Z",
        completed_at: null,
      };

      store.activeAnalysisJobs = new Map([[bookId, runningJob]]);

      // Mock API to return completed status
      const completedJob = { ...runningJob, status: "completed" as const };
      vi.mocked(api.get).mockResolvedValue({ data: completedJob });

      // Start the poller
      store.startJobPoller(bookId, 1000);

      // Fast-forward to trigger poll
      await vi.advanceTimersByTimeAsync(1000);

      // Job should be cleared after completion
      expect(store.hasActiveJob(bookId)).toBe(false);
    });

    it("should clear job when status is failed", async () => {
      const store = useBooksStore();
      const bookId = 101;

      // Set up running job
      const runningJob = {
        job_id: "test-job-101",
        book_id: bookId,
        status: "running" as const,
        model: "sonnet",
        error_message: null,
        created_at: "2025-12-21T00:00:00Z",
        updated_at: "2025-12-21T00:00:00Z",
        completed_at: null,
      };

      store.activeAnalysisJobs = new Map([[bookId, runningJob]]);

      // Mock API to return failed status
      const failedJob = {
        ...runningJob,
        status: "failed" as const,
        error_message: "Analysis failed",
      };
      vi.mocked(api.get).mockResolvedValue({ data: failedJob });

      // Start the poller
      store.startJobPoller(bookId, 1000);

      // Fast-forward to trigger poll
      await vi.advanceTimersByTimeAsync(1000);

      // Job should be cleared after failure
      expect(store.hasActiveJob(bookId)).toBe(false);
    });
  });
});
