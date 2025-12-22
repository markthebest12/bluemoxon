import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useJobPolling } from '../useJobPolling'

describe('useJobPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
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
})
