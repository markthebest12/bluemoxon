import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useCleanupJobPolling } from "../useCleanupJobPolling";
import { api } from "@/services/api";

// Mock the API
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

describe("useCleanupJobPolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(api.get).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("should return inactive state when not polling", () => {
      const polling = useCleanupJobPolling();

      expect(polling.isActive.value).toBe(false);
      expect(polling.status.value).toBe(null);
      expect(polling.progressPct.value).toBe(0);
      expect(polling.error.value).toBe(null);
    });

    it("should initialize all counters to zero", () => {
      const polling = useCleanupJobPolling();

      expect(polling.deletedCount.value).toBe(0);
      expect(polling.deletedBytes.value).toBe(0);
      expect(polling.totalCount.value).toBe(0);
      expect(polling.totalBytes.value).toBe(0);
    });
  });

  describe("start() and stop()", () => {
    it("should set isActive to true when started", () => {
      const polling = useCleanupJobPolling();

      polling.start("test-job-id");

      expect(polling.isActive.value).toBe(true);
    });

    it("should set initial status to pending when started", () => {
      const polling = useCleanupJobPolling();

      polling.start("test-job-id");

      expect(polling.status.value).toBe("pending");
    });

    it("should set isActive to false when stopped", () => {
      const polling = useCleanupJobPolling();

      polling.start("test-job-id");
      polling.stop();

      expect(polling.isActive.value).toBe(false);
    });

    it("should poll the correct endpoint", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          job_id: "test-job-id",
          status: "running",
          progress_pct: 50,
          total_count: 100,
          total_bytes: 1000000,
          deleted_count: 50,
          deleted_bytes: 500000,
        },
      });

      const polling = useCleanupJobPolling();
      polling.start("test-job-id");

      // First poll happens immediately
      await vi.advanceTimersByTimeAsync(0);

      expect(api.get).toHaveBeenCalledWith("/admin/cleanup/jobs/test-job-id");

      polling.stop();
    });

    it("should update status and progress from API response", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          job_id: "test-job-id",
          status: "running",
          progress_pct: 50,
          total_count: 100,
          total_bytes: 1000000,
          deleted_count: 50,
          deleted_bytes: 500000,
        },
      });

      const polling = useCleanupJobPolling();
      polling.start("test-job-id");

      await vi.advanceTimersByTimeAsync(0);

      expect(polling.status.value).toBe("running");
      expect(polling.progressPct.value).toBe(50);
      expect(polling.deletedCount.value).toBe(50);
      expect(polling.deletedBytes.value).toBe(500000);
      expect(polling.totalCount.value).toBe(100);
      expect(polling.totalBytes.value).toBe(1000000);

      polling.stop();
    });

    it("should continue polling at specified interval", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          job_id: "test-job-id",
          status: "running",
          progress_pct: 25,
          total_count: 100,
          total_bytes: 1000000,
          deleted_count: 25,
          deleted_bytes: 250000,
        },
      });

      const polling = useCleanupJobPolling({ pollInterval: 2000 });
      polling.start("test-job-id");

      // Initial poll
      await vi.advanceTimersByTimeAsync(0);
      expect(api.get).toHaveBeenCalledTimes(1);

      // Second poll after interval
      await vi.advanceTimersByTimeAsync(2000);
      expect(api.get).toHaveBeenCalledTimes(2);

      polling.stop();
    });

    it("should not poll after stop() is called", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          job_id: "test-job-id",
          status: "running",
          progress_pct: 50,
          total_count: 100,
          total_bytes: 1000000,
          deleted_count: 50,
          deleted_bytes: 500000,
        },
      });

      const polling = useCleanupJobPolling({ pollInterval: 2000 });
      polling.start("test-job-id");

      await vi.advanceTimersByTimeAsync(0);
      expect(api.get).toHaveBeenCalledTimes(1);

      polling.stop();

      await vi.advanceTimersByTimeAsync(4000);
      expect(api.get).toHaveBeenCalledTimes(1); // Still 1, not called again
    });

    it("should reset state when starting a new job", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          job_id: "test-job-id",
          status: "running",
          progress_pct: 50,
          total_count: 100,
          total_bytes: 1000000,
          deleted_count: 50,
          deleted_bytes: 500000,
        },
      });

      const polling = useCleanupJobPolling();
      polling.start("job-1");
      await vi.advanceTimersByTimeAsync(0);

      expect(polling.progressPct.value).toBe(50);

      // Start new job - should reset
      vi.mocked(api.get).mockResolvedValue({
        data: {
          job_id: "job-2",
          status: "pending",
          progress_pct: 0,
          total_count: 0,
          total_bytes: 0,
          deleted_count: 0,
          deleted_bytes: 0,
        },
      });

      polling.start("job-2");
      expect(polling.progressPct.value).toBe(0);
      expect(polling.status.value).toBe("pending");

      polling.stop();
    });
  });

  describe("completion detection", () => {
    it("should stop polling when job completes", async () => {
      vi.mocked(api.get)
        .mockResolvedValueOnce({
          data: {
            job_id: "test-job-id",
            status: "running",
            progress_pct: 50,
            total_count: 100,
            total_bytes: 1000000,
            deleted_count: 50,
            deleted_bytes: 500000,
          },
        })
        .mockResolvedValueOnce({
          data: {
            job_id: "test-job-id",
            status: "completed",
            progress_pct: 100,
            total_count: 100,
            total_bytes: 1000000,
            deleted_count: 100,
            deleted_bytes: 1000000,
          },
        });

      const polling = useCleanupJobPolling({ pollInterval: 2000 });
      polling.start("test-job-id");

      // First poll - running
      await vi.advanceTimersByTimeAsync(0);
      expect(polling.isActive.value).toBe(true);

      // Second poll - completed
      await vi.advanceTimersByTimeAsync(2000);
      expect(polling.isActive.value).toBe(false);
      expect(polling.status.value).toBe("completed");
      expect(polling.progressPct.value).toBe(100);
    });

    it("should stop polling when job fails", async () => {
      vi.mocked(api.get)
        .mockResolvedValueOnce({
          data: {
            job_id: "test-job-id",
            status: "running",
            progress_pct: 25,
            total_count: 100,
            total_bytes: 1000000,
            deleted_count: 25,
            deleted_bytes: 250000,
          },
        })
        .mockResolvedValueOnce({
          data: {
            job_id: "test-job-id",
            status: "failed",
            progress_pct: 25,
            total_count: 100,
            total_bytes: 1000000,
            deleted_count: 25,
            deleted_bytes: 250000,
            error_message: "S3 access denied",
          },
        });

      const polling = useCleanupJobPolling({ pollInterval: 2000 });
      polling.start("test-job-id");

      await vi.advanceTimersByTimeAsync(0);
      await vi.advanceTimersByTimeAsync(2000);

      expect(polling.isActive.value).toBe(false);
      expect(polling.status.value).toBe("failed");
      expect(polling.error.value).toBe("S3 access denied");
    });

    it("should emit onComplete callback when job completes", async () => {
      const completedData = {
        job_id: "test-job-id",
        status: "completed" as const,
        progress_pct: 100,
        total_count: 100,
        total_bytes: 1000000,
        deleted_count: 100,
        deleted_bytes: 1000000,
      };

      vi.mocked(api.get).mockResolvedValueOnce({ data: completedData });

      const onComplete = vi.fn();
      const polling = useCleanupJobPolling({ onComplete });
      polling.start("test-job-id");

      await vi.advanceTimersByTimeAsync(0);

      expect(onComplete).toHaveBeenCalledWith(completedData);
    });

    it("should emit onError callback when job fails", async () => {
      vi.mocked(api.get).mockResolvedValueOnce({
        data: {
          job_id: "test-job-id",
          status: "failed",
          progress_pct: 25,
          total_count: 100,
          total_bytes: 1000000,
          deleted_count: 25,
          deleted_bytes: 250000,
          error_message: "Permission denied",
        },
      });

      const onError = vi.fn();
      const polling = useCleanupJobPolling({ onError });
      polling.start("test-job-id");

      await vi.advanceTimersByTimeAsync(0);

      expect(onError).toHaveBeenCalledWith("Permission denied");
    });
  });

  describe("error handling", () => {
    it("should stop polling and set error on API failure", async () => {
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      const polling = useCleanupJobPolling();
      polling.start("test-job-id");

      await vi.advanceTimersByTimeAsync(0);

      expect(polling.isActive.value).toBe(false);
      expect(polling.error.value).toBe("Network error");
    });

    it("should set generic error message when error has no message", async () => {
      vi.mocked(api.get).mockRejectedValueOnce({});

      const polling = useCleanupJobPolling();
      polling.start("test-job-id");

      await vi.advanceTimersByTimeAsync(0);

      expect(polling.error.value).toBe("Failed to fetch status");
    });
  });

  describe("custom poll interval", () => {
    it("should use custom poll interval when provided", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          job_id: "test-job-id",
          status: "running",
          progress_pct: 50,
          total_count: 100,
          total_bytes: 1000000,
          deleted_count: 50,
          deleted_bytes: 500000,
        },
      });

      const polling = useCleanupJobPolling({ pollInterval: 1000 });
      polling.start("test-job-id");

      // Initial poll
      await vi.advanceTimersByTimeAsync(0);
      expect(api.get).toHaveBeenCalledTimes(1);

      // Should poll at 1000ms, not default 2000ms
      await vi.advanceTimersByTimeAsync(1000);
      expect(api.get).toHaveBeenCalledTimes(2);

      polling.stop();
    });
  });
});
