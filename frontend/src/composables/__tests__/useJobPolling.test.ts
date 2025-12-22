import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useJobPolling } from '../useJobPolling'
import { api } from '@/services/api'

// Mock the API
vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

describe('useJobPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(api.get).mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('should return inactive state when not polling', () => {
      const polling = useJobPolling('analysis')

      expect(polling.isActive.value).toBe(false)
      expect(polling.status.value).toBe(null)
      expect(polling.error.value).toBe(null)
    })

    it('should have correct poll interval for analysis jobs', () => {
      const polling = useJobPolling('analysis')
      expect(polling.pollInterval).toBe(5000)
    })

    it('should have correct poll interval for eval-runbook jobs', () => {
      const polling = useJobPolling('eval-runbook')
      expect(polling.pollInterval).toBe(3000)
    })
  })

  describe('start() and stop()', () => {
    it('should set isActive to true when started', () => {
      const polling = useJobPolling('analysis')

      polling.start(123)

      expect(polling.isActive.value).toBe(true)
    })

    it('should set isActive to false when stopped', () => {
      const polling = useJobPolling('analysis')

      polling.start(123)
      polling.stop()

      expect(polling.isActive.value).toBe(false)
    })

    it('should poll the correct endpoint for analysis', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { status: 'running', job_id: 'abc', book_id: 123 }
      })

      const polling = useJobPolling('analysis')
      polling.start(123)

      // Advance timer to trigger first poll
      await vi.advanceTimersByTimeAsync(5000)

      expect(api.get).toHaveBeenCalledWith('/books/123/analysis/status')

      polling.stop()
    })

    it('should poll the correct endpoint for eval-runbook', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { status: 'running', job_id: 'abc', book_id: 123 }
      })

      const polling = useJobPolling('eval-runbook')
      polling.start(123)

      await vi.advanceTimersByTimeAsync(3000)

      expect(api.get).toHaveBeenCalledWith('/books/123/eval-runbook/status')

      polling.stop()
    })

    it('should update status from API response', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { status: 'running', job_id: 'abc', book_id: 123 }
      })

      const polling = useJobPolling('analysis')
      polling.start(123)

      await vi.advanceTimersByTimeAsync(5000)

      expect(polling.status.value).toBe('running')

      polling.stop()
    })

    it('should not poll after stop() is called', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { status: 'running', job_id: 'abc', book_id: 123 }
      })

      const polling = useJobPolling('analysis')
      polling.start(123)

      await vi.advanceTimersByTimeAsync(5000)
      expect(api.get).toHaveBeenCalledTimes(1)

      polling.stop()

      await vi.advanceTimersByTimeAsync(10000)
      expect(api.get).toHaveBeenCalledTimes(1) // Still 1, not called again
    })
  })
})
