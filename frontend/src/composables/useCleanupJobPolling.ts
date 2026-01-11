import { ref, readonly, onUnmounted } from "vue";
import { api } from "@/services/api";

export type CleanupJobStatus = "pending" | "running" | "completed" | "failed" | null;

export interface CleanupJobData {
  job_id: string;
  status: CleanupJobStatus;
  progress_pct: number;
  total_count: number;
  total_bytes: number;
  deleted_count: number;
  deleted_bytes: number;
  error_message?: string;
}

export interface UseCleanupJobPollingOptions {
  onComplete?: (data: CleanupJobData) => void;
  onError?: (error: string) => void;
  pollInterval?: number;
}

export function useCleanupJobPolling(options: UseCleanupJobPollingOptions = {}) {
  const { pollInterval = 2000 } = options;

  const isActive = ref(false);
  const status = ref<CleanupJobStatus>(null);
  const progressPct = ref(0);
  const deletedCount = ref(0);
  const deletedBytes = ref(0);
  const totalCount = ref(0);
  const totalBytes = ref(0);
  const error = ref<string | null>(null);

  let intervalId: ReturnType<typeof setInterval> | null = null;
  let currentJobId: string | null = null;

  async function poll() {
    if (!currentJobId) return;

    try {
      const response = await api.get(`/admin/cleanup/jobs/${currentJobId}`);
      const data = response.data as CleanupJobData;

      status.value = data.status;
      progressPct.value = data.progress_pct;
      deletedCount.value = data.deleted_count;
      deletedBytes.value = data.deleted_bytes;
      totalCount.value = data.total_count;
      totalBytes.value = data.total_bytes;

      if (data.error_message) {
        error.value = data.error_message;
      }

      if (data.status === "completed") {
        stop();
        options.onComplete?.(data);
      } else if (data.status === "failed") {
        stop();
        options.onError?.(error.value || "Cleanup job failed");
      }
    } catch (e: unknown) {
      console.error("Failed to poll cleanup job status:", e);
      const err = e as { message?: string };
      error.value = err.message || "Failed to fetch status";
      stop();
    }
  }

  function start(jobId: string) {
    stop(); // Clear any existing poller
    currentJobId = jobId;
    isActive.value = true;
    status.value = "pending";
    error.value = null;
    progressPct.value = 0;

    // Initial poll immediately
    void poll();

    intervalId = setInterval(() => {
      poll().catch((err: unknown) => {
        console.error("Cleanup job polling error:", err);
        stop();
      });
    }, pollInterval);
  }

  function stop() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
    isActive.value = false;
    currentJobId = null;
  }

  // Auto-cleanup on unmount
  onUnmounted(() => {
    stop();
  });

  return {
    isActive: readonly(isActive),
    status: readonly(status),
    progressPct: readonly(progressPct),
    deletedCount: readonly(deletedCount),
    deletedBytes: readonly(deletedBytes),
    totalCount: readonly(totalCount),
    totalBytes: readonly(totalBytes),
    error: readonly(error),
    start,
    stop,
  };
}
