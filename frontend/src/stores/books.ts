import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";

export interface AnalysisJob {
  job_id: string;
  book_id: number;
  status: "pending" | "running" | "completed" | "failed";
  model: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface EvalRunbookJob {
  job_id: string;
  book_id: number;
  status: "pending" | "running" | "completed" | "failed";
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface Book {
  id: number;
  title: string;
  author: { id: number; name: string } | null;
  publisher: { id: number; name: string; tier: string | null } | null;
  binder: { id: number; name: string } | null;
  publication_date: string | null;
  edition: string | null;
  volumes: number;
  category: string | null;
  inventory_type: string;
  binding_type: string | null;
  binding_authenticated: boolean;
  binding_description: string | null;
  condition_grade: string | null;
  condition_notes: string | null;
  value_low: number | null;
  value_mid: number | null;
  value_high: number | null;
  purchase_price: number | null;
  acquisition_cost: number | null;
  purchase_date: string | null;
  purchase_source: string | null;
  discount_pct: number | null;
  roi_pct: number | null;
  status: string;
  notes: string | null;
  provenance: string | null;
  has_analysis: boolean;
  has_eval_runbook: boolean;
  image_count: number;
  primary_image_url: string | null;
  investment_grade: number | null;
  strategic_fit: number | null;
  collection_impact: number | null;
  overall_score: number | null;
  scores_calculated_at: string | null;
  // Source tracking
  source_url: string | null;
  source_item_id: string | null;
  estimated_delivery: string | null;
  // Archive tracking
  source_archived_url: string | null;
  archive_status: "pending" | "success" | "failed" | null;
}

interface Filters {
  q?: string;
  inventory_type?: string;
  category?: string;
  status?: string;
  publisher_id?: number;
  publisher_tier?: string;
  author_id?: number;
  binder_id?: number;
  binding_authenticated?: boolean;
  binding_type?: string;
  condition_grade?: string;
  min_value?: number;
  max_value?: number;
  year_start?: number;
  year_end?: number;
  has_images?: boolean;
  has_analysis?: boolean;
  has_provenance?: boolean;
}

export const useBooksStore = defineStore("books", () => {
  const books = ref<Book[]>([]);
  const currentBook = ref<Book | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Analysis job tracking (book_id -> job)
  const activeAnalysisJobs = ref<Map<number, AnalysisJob>>(new Map());
  const analysisJobPollers = ref<Map<number, ReturnType<typeof setInterval>>>(new Map());

  // Eval runbook job tracking (book_id -> job)
  const activeEvalRunbookJobs = ref<Map<number, EvalRunbookJob>>(new Map());
  const evalRunbookJobPollers = ref<Map<number, ReturnType<typeof setInterval>>>(new Map());

  const page = ref(1);
  const perPage = ref(20);
  const total = ref(0);
  const filters = ref<Filters>({});
  const sortBy = ref("title");
  const sortOrder = ref<"asc" | "desc">("asc");

  const totalPages = computed(() => Math.ceil(total.value / perPage.value));

  async function fetchBooks() {
    loading.value = true;
    error.value = null;
    try {
      const params = {
        page: page.value,
        per_page: perPage.value,
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
        ...filters.value,
      };
      const response = await api.get("/books", { params });
      books.value = response.data.items;
      total.value = response.data.total;
    } catch (e: any) {
      error.value = e.message || "Failed to fetch books";
    } finally {
      loading.value = false;
    }
  }

  async function fetchBook(id: number) {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get(`/books/${id}`);
      currentBook.value = response.data;
    } catch (e: any) {
      error.value = e.message || "Failed to fetch book";
    } finally {
      loading.value = false;
    }
  }

  async function createBook(bookData: Partial<Book>) {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.post("/books", bookData);
      return response.data;
    } catch (e: any) {
      error.value = e.message || "Failed to create book";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  interface DuplicateMatch {
    id: number;
    title: string;
    author_name: string | null;
    status: string;
    similarity_score: number;
  }

  interface DuplicateCheckResponse {
    has_duplicates: boolean;
    matches: DuplicateMatch[];
  }

  async function checkDuplicate(
    title: string,
    authorId?: number | null
  ): Promise<DuplicateCheckResponse> {
    const response = await api.post("/books/check-duplicate", {
      title,
      author_id: authorId || undefined,
    });
    return response.data;
  }

  async function updateBook(id: number, bookData: Partial<Book>) {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.put(`/books/${id}`, bookData);
      currentBook.value = response.data;
      return response.data;
    } catch (e: any) {
      error.value = e.message || "Failed to update book";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteBook(id: number) {
    loading.value = true;
    error.value = null;
    try {
      await api.delete(`/books/${id}`);
    } catch (e: any) {
      error.value = e.message || "Failed to delete book";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateAnalysis(bookId: number, markdown: string) {
    try {
      await api.put(`/books/${bookId}/analysis`, markdown, {
        headers: { "Content-Type": "text/plain" },
      });
      // Update has_analysis flag on current book if loaded
      if (currentBook.value && currentBook.value.id === bookId) {
        currentBook.value.has_analysis = true;
      }
    } catch (e: any) {
      error.value = e.message || "Failed to update analysis";
      throw e;
    }
  }

  async function generateAnalysis(
    bookId: number,
    model: "sonnet" | "opus" = "sonnet"
  ): Promise<{
    id: number;
    book_id: number;
    model_used: string;
    full_markdown: string;
    generated_at: string;
  }> {
    const response = await api.post(`/books/${bookId}/analysis/generate`, {
      model,
    });

    // Update currentBook if it matches
    if (currentBook.value?.id === bookId) {
      currentBook.value.has_analysis = true;
    }

    return response.data;
  }

  /**
   * Start async analysis generation job.
   * Returns immediately with job info, poll status for completion.
   */
  async function generateAnalysisAsync(
    bookId: number,
    model: "sonnet" | "opus" = "sonnet"
  ): Promise<AnalysisJob> {
    const response = await api.post(`/books/${bookId}/analysis/generate-async`, { model });
    const job = response.data as AnalysisJob;

    // Track the job
    activeAnalysisJobs.value.set(bookId, job);

    // Start polling for status
    startJobPoller(bookId);

    return job;
  }

  /**
   * Get latest analysis job status for a book.
   */
  async function fetchAnalysisJobStatus(bookId: number): Promise<AnalysisJob> {
    const response = await api.get(`/books/${bookId}/analysis/status`);
    const job = response.data as AnalysisJob;

    // Update tracked job
    activeAnalysisJobs.value.set(bookId, job);

    return job;
  }

  /**
   * Start polling for job status updates.
   */
  function startJobPoller(bookId: number, intervalMs: number = 5000) {
    // Clear any existing poller for this book
    stopJobPoller(bookId);

    const poller = setInterval(async () => {
      try {
        const job = await fetchAnalysisJobStatus(bookId);

        if (job.status === "completed" || job.status === "failed") {
          stopJobPoller(bookId);

          // Update book's has_analysis flag if completed
          if (job.status === "completed" && currentBook.value?.id === bookId) {
            currentBook.value.has_analysis = true;
          }
        }
      } catch (e) {
        console.error(`Failed to poll job status for book ${bookId}:`, e);
        // Stop polling on error (job might not exist)
        stopJobPoller(bookId);
      }
    }, intervalMs);

    analysisJobPollers.value.set(bookId, poller);
  }

  /**
   * Stop polling for a book's job status.
   */
  function stopJobPoller(bookId: number) {
    const existingPoller = analysisJobPollers.value.get(bookId);
    if (existingPoller) {
      clearInterval(existingPoller);
      analysisJobPollers.value.delete(bookId);
    }
  }

  /**
   * Get active analysis job for a book (if any).
   */
  function getActiveJob(bookId: number): AnalysisJob | undefined {
    return activeAnalysisJobs.value.get(bookId);
  }

  /**
   * Check if a book has an active (pending/running) analysis job.
   */
  function hasActiveJob(bookId: number): boolean {
    const job = activeAnalysisJobs.value.get(bookId);
    return !!job && (job.status === "pending" || job.status === "running");
  }

  /**
   * Clear completed/failed job from tracking.
   */
  function clearJob(bookId: number) {
    activeAnalysisJobs.value.delete(bookId);
    stopJobPoller(bookId);
  }

  // ============ Eval Runbook Job Functions ============

  /**
   * Start async eval runbook generation job.
   * Returns immediately with job info, poll status for completion.
   */
  async function generateEvalRunbookAsync(bookId: number): Promise<EvalRunbookJob> {
    const response = await api.post(`/books/${bookId}/eval-runbook/generate`);
    const job = response.data as EvalRunbookJob;

    // Track the job
    activeEvalRunbookJobs.value.set(bookId, job);

    // Start polling for status
    startEvalRunbookJobPoller(bookId);

    return job;
  }

  /**
   * Get latest eval runbook job status for a book.
   */
  async function fetchEvalRunbookJobStatus(bookId: number): Promise<EvalRunbookJob> {
    const response = await api.get(`/books/${bookId}/eval-runbook/status`);
    const job = response.data as EvalRunbookJob;

    // Update tracked job
    activeEvalRunbookJobs.value.set(bookId, job);

    return job;
  }

  /**
   * Start polling for eval runbook job status updates.
   */
  function startEvalRunbookJobPoller(bookId: number, intervalMs: number = 5000) {
    // Clear any existing poller for this book
    stopEvalRunbookJobPoller(bookId);

    const poller = setInterval(async () => {
      try {
        const job = await fetchEvalRunbookJobStatus(bookId);

        if (job.status === "completed" || job.status === "failed") {
          stopEvalRunbookJobPoller(bookId);

          // Update book's has_eval_runbook flag if completed
          if (job.status === "completed" && currentBook.value?.id === bookId) {
            currentBook.value.has_eval_runbook = true;
          }
        }
      } catch (e) {
        console.error(`Failed to poll eval runbook job status for book ${bookId}:`, e);
        // Stop polling on error (job might not exist)
        stopEvalRunbookJobPoller(bookId);
      }
    }, intervalMs);

    evalRunbookJobPollers.value.set(bookId, poller);
  }

  /**
   * Stop polling for a book's eval runbook job status.
   */
  function stopEvalRunbookJobPoller(bookId: number) {
    const existingPoller = evalRunbookJobPollers.value.get(bookId);
    if (existingPoller) {
      clearInterval(existingPoller);
      evalRunbookJobPollers.value.delete(bookId);
    }
  }

  /**
   * Get active eval runbook job for a book (if any).
   */
  function getActiveEvalRunbookJob(bookId: number): EvalRunbookJob | undefined {
    return activeEvalRunbookJobs.value.get(bookId);
  }

  /**
   * Check if a book has an active (pending/running) eval runbook job.
   */
  function hasActiveEvalRunbookJob(bookId: number): boolean {
    const job = activeEvalRunbookJobs.value.get(bookId);
    return !!job && (job.status === "pending" || job.status === "running");
  }

  /**
   * Clear completed/failed eval runbook job from tracking.
   */
  function clearEvalRunbookJob(bookId: number) {
    activeEvalRunbookJobs.value.delete(bookId);
    stopEvalRunbookJobPoller(bookId);
  }

  async function calculateScores(bookId: number) {
    const response = await api.post(`/books/${bookId}/scores/calculate`);
    return response.data;
  }

  async function fetchScoreBreakdown(bookId: number) {
    const response = await api.get(`/books/${bookId}/scores/breakdown`);
    return response.data;
  }

  async function archiveSource(bookId: number): Promise<Book> {
    const response = await api.post(`/books/${bookId}/archive-source`);
    // Update currentBook if it matches
    if (currentBook.value?.id === bookId) {
      currentBook.value = response.data;
    }
    return response.data;
  }

  function setFilters(newFilters: Filters) {
    filters.value = newFilters;
    page.value = 1;
    fetchBooks();
  }

  function setSort(field: string, order: "asc" | "desc") {
    sortBy.value = field;
    sortOrder.value = order;
    fetchBooks();
  }

  function setPage(newPage: number) {
    page.value = newPage;
    fetchBooks();
  }

  return {
    books,
    currentBook,
    loading,
    error,
    page,
    perPage,
    total,
    totalPages,
    filters,
    sortBy,
    sortOrder,
    activeAnalysisJobs,
    activeEvalRunbookJobs,
    fetchBooks,
    fetchBook,
    createBook,
    checkDuplicate,
    updateBook,
    deleteBook,
    updateAnalysis,
    generateAnalysis,
    generateAnalysisAsync,
    fetchAnalysisJobStatus,
    getActiveJob,
    hasActiveJob,
    clearJob,
    // Eval runbook job functions
    generateEvalRunbookAsync,
    fetchEvalRunbookJobStatus,
    getActiveEvalRunbookJob,
    hasActiveEvalRunbookJob,
    clearEvalRunbookJob,
    calculateScores,
    fetchScoreBreakdown,
    archiveSource,
    setFilters,
    setSort,
    setPage,
  };
});
