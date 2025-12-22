import { ref, readonly, onUnmounted } from 'vue'
import { api } from '@/services/api'

export type JobType = 'analysis' | 'eval-runbook'
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | null

const POLL_INTERVALS: Record<JobType, number> = {
  'analysis': 5000,
  'eval-runbook': 3000,
}

const STATUS_ENDPOINTS: Record<JobType, (bookId: number) => string> = {
  'analysis': (bookId) => `/books/${bookId}/analysis/status`,
  'eval-runbook': (bookId) => `/books/${bookId}/eval-runbook/status`,
}

export function useJobPolling(jobType: JobType) {
  const isActive = ref(false)
  const status = ref<JobStatus>(null)
  const error = ref<string | null>(null)
  const pollInterval = POLL_INTERVALS[jobType]

  let intervalId: ReturnType<typeof setInterval> | null = null
  let currentBookId: number | null = null

  async function poll() {
    if (!currentBookId) return

    try {
      const endpoint = STATUS_ENDPOINTS[jobType](currentBookId)
      const response = await api.get(endpoint)
      status.value = response.data.status

      if (response.data.error_message) {
        error.value = response.data.error_message
      }
    } catch (e: unknown) {
      console.error(`Failed to poll ${jobType} status:`, e)
      const err = e as { message?: string }
      error.value = err.message || 'Failed to fetch status'
    }
  }

  function start(bookId: number) {
    stop() // Clear any existing poller

    currentBookId = bookId
    isActive.value = true
    status.value = 'pending' // Assume pending until first poll
    error.value = null

    intervalId = setInterval(poll, pollInterval)
  }

  function stop() {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
    isActive.value = false
    currentBookId = null
  }

  // Auto-cleanup on unmount
  onUnmounted(() => {
    stop()
  })

  return {
    isActive: readonly(isActive),
    status: readonly(status),
    error: readonly(error),
    pollInterval,
    start,
    stop,
  }
}
