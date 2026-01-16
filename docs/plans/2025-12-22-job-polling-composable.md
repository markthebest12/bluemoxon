# Job Polling Composable Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace scattered polling logic with a single reusable `useJobPolling` composable that reliably detects job completion and updates UI.

**Architecture:** Create a Vue composable that encapsulates all job status polling. Components call `start(bookId)` to begin polling and react to state changes. On completion, the composable refetches book data to ensure `has_analysis`/`has_eval_runbook` flags are updated.

**Tech Stack:** Vue 3 Composition API, TypeScript, Pinia (for book refresh)

---

## Task 1: Create Composable File Structure

**Files:**

- Create: `frontend/src/composables/useJobPolling.ts`
- Create: `frontend/src/composables/__tests__/useJobPolling.test.ts`

**Step 1: Create composables directory**

```bash
mkdir -p frontend/src/composables/__tests__
```

**Step 2: Create empty composable file**

Create `frontend/src/composables/useJobPolling.ts`:

```typescript
// Placeholder - will be implemented with TDD
export {}
```

**Step 3: Commit**

```bash
git add frontend/src/composables/
git commit -m "chore: add composables directory structure (#554)"
```

---

## Task 2: Write Failing Tests for Basic Polling State

**Files:**

- Test: `frontend/src/composables/__tests__/useJobPolling.test.ts`

**Step 1: Write the failing test for initial state**

```typescript
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
```

**Step 2: Run test to verify it fails**

Run: `npm run --prefix frontend test -- --run composables/useJobPolling`

Expected: FAIL with "Cannot find module '../useJobPolling'"

**Step 3: Write minimal implementation to pass**

Update `frontend/src/composables/useJobPolling.ts`:

```typescript
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
```

**Step 4: Run test to verify it passes**

Run: `npm run --prefix frontend test -- --run composables/useJobPolling`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/composables/
git commit -m "feat: add useJobPolling composable with initial state (#554)"
```

---

## Task 3: Write Failing Tests for start() and stop()

**Files:**

- Modify: `frontend/src/composables/__tests__/useJobPolling.test.ts`
- Modify: `frontend/src/composables/useJobPolling.ts`

**Step 1: Add tests for start/stop behavior**

Add to test file:

```typescript
import { api } from '@/services/api'

// Mock the API
vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

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
```

**Step 2: Run tests to verify they fail**

Run: `npm run --prefix frontend test -- --run composables/useJobPolling`

Expected: FAIL - `polling.start is not a function`

**Step 3: Implement start() and stop()**

Update `frontend/src/composables/useJobPolling.ts`:

```typescript
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
    } catch (e: any) {
      console.error(`Failed to poll ${jobType} status:`, e)
      error.value = e.message || 'Failed to fetch status'
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
```

**Step 4: Run tests to verify they pass**

Run: `npm run --prefix frontend test -- --run composables/useJobPolling`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/composables/
git commit -m "feat: add start/stop methods to useJobPolling (#554)"
```

---

## Task 4: Write Failing Tests for Completion Detection

**Files:**

- Modify: `frontend/src/composables/__tests__/useJobPolling.test.ts`
- Modify: `frontend/src/composables/useJobPolling.ts`

**Step 1: Add tests for completion handling**

Add to test file:

```typescript
import { useBooksStore } from '@/stores/books'
import { createPinia, setActivePinia } from 'pinia'

// Mock books store
vi.mock('@/stores/books', () => ({
  useBooksStore: vi.fn(() => ({
    fetchBook: vi.fn(),
  })),
}))

describe('completion detection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.get).mockReset()
  })

  it('should stop polling when job completes', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { status: 'running' } })
      .mockResolvedValueOnce({ data: { status: 'completed' } })

    const polling = useJobPolling('analysis')
    polling.start(123)

    // First poll - running
    await vi.advanceTimersByTimeAsync(5000)
    expect(polling.isActive.value).toBe(true)

    // Second poll - completed
    await vi.advanceTimersByTimeAsync(5000)
    expect(polling.isActive.value).toBe(false)
    expect(polling.status.value).toBe('completed')
  })

  it('should stop polling when job fails', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { status: 'running' } })
      .mockResolvedValueOnce({ data: { status: 'failed', error_message: 'Out of memory' } })

    const polling = useJobPolling('analysis')
    polling.start(123)

    await vi.advanceTimersByTimeAsync(5000)
    await vi.advanceTimersByTimeAsync(5000)

    expect(polling.isActive.value).toBe(false)
    expect(polling.status.value).toBe('failed')
    expect(polling.error.value).toBe('Out of memory')
  })

  it('should refetch book data on completion', async () => {
    const mockFetchBook = vi.fn()
    vi.mocked(useBooksStore).mockReturnValue({
      fetchBook: mockFetchBook,
    } as any)

    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { status: 'running' } })
      .mockResolvedValueOnce({ data: { status: 'completed' } })

    const polling = useJobPolling('analysis')
    polling.start(123)

    await vi.advanceTimersByTimeAsync(5000)
    await vi.advanceTimersByTimeAsync(5000)

    expect(mockFetchBook).toHaveBeenCalledWith(123)
  })

  it('should emit onComplete callback when job completes', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { status: 'running' } })
      .mockResolvedValueOnce({ data: { status: 'completed' } })

    const onComplete = vi.fn()
    const polling = useJobPolling('analysis', { onComplete })
    polling.start(123)

    await vi.advanceTimersByTimeAsync(5000)
    await vi.advanceTimersByTimeAsync(5000)

    expect(onComplete).toHaveBeenCalledWith(123)
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `npm run --prefix frontend test -- --run composables/useJobPolling`

Expected: FAIL - completion detection not implemented

**Step 3: Implement completion detection**

Update `frontend/src/composables/useJobPolling.ts`:

```typescript
import { ref, readonly, onUnmounted } from 'vue'
import { api } from '@/services/api'
import { useBooksStore } from '@/stores/books'

export type JobType = 'analysis' | 'eval-runbook'
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | null

export interface UseJobPollingOptions {
  onComplete?: (bookId: number) => void
  onError?: (bookId: number, error: string) => void
}

const POLL_INTERVALS: Record<JobType, number> = {
  'analysis': 5000,
  'eval-runbook': 3000,
}

const STATUS_ENDPOINTS: Record<JobType, (bookId: number) => string> = {
  'analysis': (bookId) => `/books/${bookId}/analysis/status`,
  'eval-runbook': (bookId) => `/books/${bookId}/eval-runbook/status`,
}

export function useJobPolling(jobType: JobType, options: UseJobPollingOptions = {}) {
  const booksStore = useBooksStore()

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

      // Check for terminal states
      if (response.data.status === 'completed') {
        const bookId = currentBookId
        stop()

        // Refetch book data to update has_analysis/has_eval_runbook flags
        await booksStore.fetchBook(bookId)

        options.onComplete?.(bookId)
      } else if (response.data.status === 'failed') {
        const bookId = currentBookId
        stop()
        options.onError?.(bookId, error.value || 'Job failed')
      }
    } catch (e: any) {
      console.error(`Failed to poll ${jobType} status:`, e)
      error.value = e.message || 'Failed to fetch status'
      // Stop polling on error (job might not exist)
      stop()
    }
  }

  function start(bookId: number) {
    stop()

    currentBookId = bookId
    isActive.value = true
    status.value = 'pending'
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
```

**Step 4: Run tests to verify they pass**

Run: `npm run --prefix frontend test -- --run composables/useJobPolling`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/composables/
git commit -m "feat: add completion detection to useJobPolling (#554)"
```

---

## Task 5: Integrate into AcquisitionsView

**Files:**

- Modify: `frontend/src/views/AcquisitionsView.vue`

**Step 1: Import and set up composable instances**

At the top of `<script setup>`, add:

```typescript
import { useJobPolling } from '@/composables/useJobPolling'

// Job polling instances per book
const analysisPollers = ref<Map<number, ReturnType<typeof useJobPolling>>>(new Map())
const evalRunbookPollers = ref<Map<number, ReturnType<typeof useJobPolling>>>(new Map())

function getOrCreateAnalysisPoller(bookId: number) {
  if (!analysisPollers.value.has(bookId)) {
    const poller = useJobPolling('analysis', {
      onComplete: () => acquisitionsStore.refreshBook(bookId),
    })
    analysisPollers.value.set(bookId, poller)
  }
  return analysisPollers.value.get(bookId)!
}

function getOrCreateEvalRunbookPoller(bookId: number) {
  if (!evalRunbookPollers.value.has(bookId)) {
    const poller = useJobPolling('eval-runbook', {
      onComplete: () => acquisitionsStore.refreshBook(bookId),
    })
    evalRunbookPollers.value.set(bookId, poller)
  }
  return evalRunbookPollers.value.get(bookId)!
}
```

**Step 2: Replace isAnalysisRunning function**

Replace:

```typescript
function isAnalysisRunning(bookId: number) {
  const job = activeAnalysisJobs.value.get(bookId);
  return !!job && (job.status === "pending" || job.status === "running");
}
```

With:

```typescript
function isAnalysisRunning(bookId: number) {
  const poller = analysisPollers.value.get(bookId)
  return poller?.isActive.value ?? false
}
```

**Step 3: Replace isEvalRunbookRunning function**

Replace:

```typescript
function isEvalRunbookRunning(bookId: number) {
  const job = activeEvalRunbookJobs.value.get(bookId);
  return !!job && (job.status === "pending" || job.status === "running");
}
```

With:

```typescript
function isEvalRunbookRunning(bookId: number) {
  const poller = evalRunbookPollers.value.get(bookId)
  return poller?.isActive.value ?? false
}
```

**Step 4: Update getJobStatus and getEvalRunbookJobStatus**

Replace:

```typescript
function getJobStatus(bookId: number) {
  return activeAnalysisJobs.value.get(bookId);
}

function getEvalRunbookJobStatus(bookId: number) {
  return activeEvalRunbookJobs.value.get(bookId);
}
```

With:

```typescript
function getJobStatus(bookId: number) {
  const poller = analysisPollers.value.get(bookId)
  return poller ? { status: poller.status.value, error_message: poller.error.value } : null
}

function getEvalRunbookJobStatus(bookId: number) {
  const poller = evalRunbookPollers.value.get(bookId)
  return poller ? { status: poller.status.value, error_message: poller.error.value } : null
}
```

**Step 5: Update handleGenerateAnalysis**

Replace:

```typescript
async function handleGenerateAnalysis(bookId: number) {
  if (isAnalysisRunning(bookId) || startingAnalysis.value === bookId) return;

  startingAnalysis.value = bookId;
  try {
    await booksStore.generateAnalysisAsync(bookId);
  } catch (e: any) {
    // ...
  } finally {
    startingAnalysis.value = null;
  }
}
```

With:

```typescript
async function handleGenerateAnalysis(bookId: number) {
  if (isAnalysisRunning(bookId) || startingAnalysis.value === bookId) return;

  startingAnalysis.value = bookId;
  try {
    await api.post(`/books/${bookId}/analysis/generate-async`, { model: 'sonnet' });
    const poller = getOrCreateAnalysisPoller(bookId);
    poller.start(bookId);
  } catch (e: any) {
    console.error("Failed to start analysis:", e);
    const message = e.response?.data?.detail || e.message || "Failed to start analysis";
    alert(message);
  } finally {
    startingAnalysis.value = null;
  }
}
```

**Step 6: Update handleGenerateEvalRunbook**

Replace:

```typescript
async function handleGenerateEvalRunbook(bookId: number) {
  if (isEvalRunbookRunning(bookId) || startingEvalRunbook.value === bookId) return;

  startingEvalRunbook.value = bookId;
  try {
    await booksStore.generateEvalRunbookAsync(bookId);
  } catch (err) {
    console.error("Failed to start eval runbook generation:", err);
  } finally {
    startingEvalRunbook.value = null;
  }
}
```

With:

```typescript
async function handleGenerateEvalRunbook(bookId: number) {
  if (isEvalRunbookRunning(bookId) || startingEvalRunbook.value === bookId) return;

  startingEvalRunbook.value = bookId;
  try {
    await api.post(`/books/${bookId}/eval-runbook/generate`);
    const poller = getOrCreateEvalRunbookPoller(bookId);
    poller.start(bookId);
  } catch (err) {
    console.error("Failed to start eval runbook generation:", err);
  } finally {
    startingEvalRunbook.value = null;
  }
}
```

**Step 7: Update syncBackendJobPolling**

Replace:

```typescript
function syncBackendJobPolling() {
  for (const book of evaluating.value) {
    if (
      (book.eval_runbook_job_status === "running" || book.eval_runbook_job_status === "pending") &&
      !activeEvalRunbookJobs.value.has(book.id)
    ) {
      booksStore.startEvalRunbookJobPoller(book.id);
    }

    if (
      (book.analysis_job_status === "running" || book.analysis_job_status === "pending") &&
      !activeAnalysisJobs.value.has(book.id)
    ) {
      booksStore.startJobPoller(book.id);
    }
  }
}
```

With:

```typescript
function syncBackendJobPolling() {
  for (const book of evaluating.value) {
    // Start polling for any running eval runbook jobs
    if (
      (book.eval_runbook_job_status === "running" || book.eval_runbook_job_status === "pending") &&
      !isEvalRunbookRunning(book.id)
    ) {
      const poller = getOrCreateEvalRunbookPoller(book.id);
      poller.start(book.id);
    }

    // Start polling for any running analysis jobs
    if (
      (book.analysis_job_status === "running" || book.analysis_job_status === "pending") &&
      !isAnalysisRunning(book.id)
    ) {
      const poller = getOrCreateAnalysisPoller(book.id);
      poller.start(book.id);
    }
  }
}
```

**Step 8: Remove old polling code**

Remove:

```typescript
const { activeAnalysisJobs, activeEvalRunbookJobs } = storeToRefs(booksStore);

const jobCheckInterval = ref<ReturnType<typeof setInterval> | null>(null);

// And the entire onMounted jobCheckInterval logic (lines 271-307)
// And the onUnmounted cleanup for jobCheckInterval
```

**Step 9: Run lint and type check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

Expected: PASS

**Step 10: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "refactor: use useJobPolling composable in AcquisitionsView (#554)"
```

---

## Task 6: Integrate into BookDetailView

**Files:**

- Modify: `frontend/src/views/BookDetailView.vue`

**Step 1: Import composable and replace local polling**

At the top of `<script setup>`, add:

```typescript
import { useJobPolling } from '@/composables/useJobPolling'

const analysisPoller = useJobPolling('analysis')
```

**Step 2: Remove old polling state and functions**

Remove:

```typescript
let analysisPollingInterval: ReturnType<typeof setInterval> | null = null;
const ANALYSIS_POLL_INTERVAL = 5000;

function startAnalysisPolling() { ... }
function stopAnalysisPolling() { ... }

// And the watch() for analysis_job_status
// And onUnmounted cleanup for stopAnalysisPolling
```

**Step 3: Replace isAnalysisRunning function**

Replace:

```typescript
function isAnalysisRunning(): boolean {
  if (!booksStore.currentBook) return false;
  return booksStore.hasActiveJob(booksStore.currentBook.id);
}
```

With:

```typescript
function isAnalysisRunning(): boolean {
  return analysisPoller.isActive.value
}
```

**Step 4: Replace getJobStatus function**

Replace:

```typescript
function getJobStatus() {
  if (!booksStore.currentBook) return null;
  return booksStore.getActiveJob(booksStore.currentBook.id);
}
```

With:

```typescript
function getJobStatus() {
  return analysisPoller.status.value ? { status: analysisPoller.status.value } : null
}
```

**Step 5: Update handleGenerateAnalysis**

Replace:

```typescript
async function handleGenerateAnalysis() {
  const book = booksStore.currentBook;
  if (!book || isAnalysisRunning() || startingAnalysis.value) return;

  startingAnalysis.value = true;
  try {
    await booksStore.generateAnalysisAsync(book.id, selectedModel.value);
  } catch (e: unknown) {
    // ...
  } finally {
    startingAnalysis.value = false;
  }
}
```

With:

```typescript
async function handleGenerateAnalysis() {
  const book = booksStore.currentBook;
  if (!book || isAnalysisRunning() || startingAnalysis.value) return;

  startingAnalysis.value = true;
  try {
    await api.post(`/books/${book.id}/analysis/generate-async`, { model: selectedModel.value });
    analysisPoller.start(book.id);
  } catch (e: unknown) {
    console.error("Failed to start analysis:", e);
    const err = e as { response?: { data?: { detail?: string } }; message?: string };
    const message = err.response?.data?.detail || err.message || "Failed to start analysis";
    alert(message);
  } finally {
    startingAnalysis.value = false;
  }
}
```

**Step 6: Add watch for backend job status on mount**

Add after onMounted:

```typescript
// Start polling if book already has a running job
watch(
  () => booksStore.currentBook?.analysis_job_status,
  (newStatus) => {
    if (newStatus === 'running' || newStatus === 'pending') {
      if (!analysisPoller.isActive.value && booksStore.currentBook) {
        analysisPoller.start(booksStore.currentBook.id)
      }
    }
  },
  { immediate: true }
)
```

**Step 7: Run lint and type check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

Expected: PASS

**Step 8: Commit**

```bash
git add frontend/src/views/BookDetailView.vue
git commit -m "refactor: use useJobPolling composable in BookDetailView (#554)"
```

---

## Task 7: Clean Up books.ts Store

**Files:**

- Modify: `frontend/src/stores/books.ts`

**Step 1: Remove polling-related state**

Remove these declarations (lines 106-112):

```typescript
// Analysis job tracking (book_id -> job)
const activeAnalysisJobs = ref<Map<number, AnalysisJob>>(new Map());
const analysisJobPollers = ref<Map<number, ReturnType<typeof setInterval>>>(new Map());

// Eval runbook job tracking (book_id -> job)
const activeEvalRunbookJobs = ref<Map<number, EvalRunbookJob>>(new Map());
const evalRunbookJobPollers = ref<Map<number, ReturnType<typeof setInterval>>>(new Map());
```

**Step 2: Remove analysis job polling functions**

Remove these functions (lines 260-363):

- `generateAnalysisAsync`
- `fetchAnalysisJobStatus`
- `startJobPoller`
- `stopJobPoller`
- `getActiveJob`
- `hasActiveJob`
- `clearJob`

**Step 3: Remove eval runbook job polling functions**

Remove these functions (lines 365-467):

- `generateEvalRunbookAsync`
- `fetchEvalRunbookJobStatus`
- `startEvalRunbookJobPoller`
- `stopEvalRunbookJobPoller`
- `getActiveEvalRunbookJob`
- `hasActiveEvalRunbookJob`
- `clearEvalRunbookJob`

**Step 4: Update return statement**

Remove from return object:

```typescript
activeAnalysisJobs,
activeEvalRunbookJobs,
generateAnalysisAsync,
fetchAnalysisJobStatus,
getActiveJob,
hasActiveJob,
clearJob,
generateEvalRunbookAsync,
fetchEvalRunbookJobStatus,
getActiveEvalRunbookJob,
hasActiveEvalRunbookJob,
clearEvalRunbookJob,
startJobPoller,
startEvalRunbookJobPoller,
```

**Step 5: Run lint and type check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

Expected: PASS

**Step 6: Commit**

```bash
git add frontend/src/stores/books.ts
git commit -m "refactor: remove polling logic from books store (#554)"
```

---

## Task 8: Test on Staging

**Step 1: Run all frontend tests**

Run: `npm run --prefix frontend test`

Expected: All tests pass

**Step 2: Run lint and type check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

Expected: No errors

**Step 3: Build frontend**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 4: Create PR**

```bash
git push -u origin feat/job-polling-composable
gh pr create --base staging --title "feat: Replace polling with useJobPolling composable (#554)" --body "$(cat <<'EOF'
## Summary
- Created `useJobPolling` composable to manage job status polling
- Integrated into AcquisitionsView and BookDetailView
- Removed redundant polling code from books.ts store
- Fixed spinner/status stuck issues (#554)

## Changes
- NEW: `frontend/src/composables/useJobPolling.ts`
- NEW: `frontend/src/composables/__tests__/useJobPolling.test.ts`
- MODIFIED: `frontend/src/views/AcquisitionsView.vue`
- MODIFIED: `frontend/src/views/BookDetailView.vue`
- MODIFIED: `frontend/src/stores/books.ts`

## Test Plan
- [ ] Analysis job shows spinner while running
- [ ] Analysis job spinner disappears when complete
- [ ] "View Analysis" link appears after completion
- [ ] Eval runbook job shows spinner while running
- [ ] Eval runbook spinner disappears when complete
- [ ] "Eval Runbook" link appears after completion
- [ ] No stuck spinners after browser refresh
- [ ] Multiple books can poll independently

## Related
Fixes #554
EOF
)"
```

**Step 5: Wait for CI**

Run: `gh pr checks --watch`

Expected: All checks pass

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/composables/useJobPolling.ts` | CREATE | The new polling composable |
| `frontend/src/composables/__tests__/useJobPolling.test.ts` | CREATE | Unit tests |
| `frontend/src/views/AcquisitionsView.vue` | MODIFY | Use composable, remove old polling |
| `frontend/src/views/BookDetailView.vue` | MODIFY | Use composable, remove old polling |
| `frontend/src/stores/books.ts` | MODIFY | Remove all polling code |
