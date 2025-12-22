import { ref, readonly } from 'vue'

export type JobType = 'analysis' | 'eval-runbook'
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | null

const POLL_INTERVALS: Record<JobType, number> = {
  'analysis': 5000,      // 5 seconds (jobs ~5 min)
  'eval-runbook': 3000,  // 3 seconds (jobs <1 min)
}

export function useJobPolling(jobType: JobType) {
  const isActive = ref(false)
  const status = ref<JobStatus>(null)
  const error = ref<string | null>(null)
  const pollInterval = POLL_INTERVALS[jobType]

  return {
    isActive: readonly(isActive),
    status: readonly(status),
    error: readonly(error),
    pollInterval,
  }
}
