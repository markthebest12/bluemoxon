import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";
import { BOOK_STATUSES, FILTERS, PAGINATION } from "@/constants";

export interface AcquisitionBook {
  id: number;
  title: string;
  author?: { id: number; name: string };
  publisher?: { id: number; name: string; tier?: string };
  binder?: { id: number; name: string };
  status: string;
  value_low?: number;
  value_mid?: number;
  value_high?: number;
  purchase_price?: number;
  purchase_date?: string;
  discount_pct?: number;
  estimated_delivery?: string;
  estimated_delivery_end?: string;
  scoring_snapshot?: Record<string, unknown>;
  primary_image_url?: string;
  has_analysis?: boolean;
  has_eval_runbook?: boolean;
  eval_runbook_job_status?: "pending" | "running" | null;
  analysis_job_status?: "pending" | "running" | null;
  analysis_issues?: string[] | null; // truncated, degraded, missing_condition, missing_market
  investment_grade?: number | null;
  strategic_fit?: number | null;
  collection_impact?: number | null;
  overall_score?: number | null;
  scores_calculated_at?: string | null;
  volumes?: number;
  is_complete?: boolean;
  source_url?: string;
  source_archived_url: string | null;
  archive_status: "pending" | "success" | "failed" | null;
  // Shipment tracking
  tracking_number?: string | null;
  tracking_carrier?: string | null;
  tracking_url?: string | null;
  tracking_status?: string | null;
  tracking_last_checked?: string | null;
  ship_date?: string | null;
}

export interface AcquirePayload {
  purchase_price: number;
  purchase_date: string;
  order_number: string;
  place_of_purchase: string;
  estimated_delivery?: string;
  tracking_number?: string;
  tracking_carrier?: string;
}

export interface WatchlistPayload {
  title: string;
  author_id: number;
  publisher_id?: number;
  binder_id?: number;
  publication_date?: string;
  volumes?: number;
  source_url?: string;
  purchase_price?: number; // This is the asking price for watchlist items
}

export interface UpdateWatchlistPayload {
  value_low?: number;
  value_mid?: number;
  value_high?: number;
  volumes?: number;
  is_complete?: boolean;
  source_url?: string;
  purchase_price?: number; // Asking price - updating this triggers eval runbook refresh
}

export interface TrackingPayload {
  tracking_number?: string;
  tracking_carrier?: string;
  tracking_url?: string;
}

export const useAcquisitionsStore = defineStore("acquisitions", () => {
  // State
  const evaluating = ref<AcquisitionBook[]>([]);
  const inTransit = ref<AcquisitionBook[]>([]);
  const received = ref<AcquisitionBook[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Computed
  const evaluatingCount = computed(() => evaluating.value.length);
  const inTransitCount = computed(() => inTransit.value.length);
  const receivedCount = computed(() => received.value.length);

  // Actions
  async function fetchAll() {
    loading.value = true;
    error.value = null;

    try {
      const [evalRes, transitRes, receivedRes] = await Promise.all([
        api.get("/books", {
          params: {
            status: BOOK_STATUSES.EVALUATING,
            inventory_type: "PRIMARY",
            per_page: PAGINATION.DEFAULT_PER_PAGE,
            sort_by: "updated_at",
            sort_order: "desc",
          },
        }),
        api.get("/books", {
          params: {
            status: BOOK_STATUSES.IN_TRANSIT,
            inventory_type: "PRIMARY",
            per_page: PAGINATION.DEFAULT_PER_PAGE,
            sort_by: "updated_at",
            sort_order: "desc",
          },
        }),
        api.get("/books", {
          params: {
            status: BOOK_STATUSES.ON_HAND,
            inventory_type: "PRIMARY",
            per_page: PAGINATION.RECEIVED_PER_PAGE,
            sort_by: "updated_at",
            sort_order: "desc",
          },
        }),
      ]);

      evaluating.value = evalRes.data.items;
      inTransit.value = transitRes.data.items;

      // Only show items received within lookback window
      const lookbackDate = new Date();
      lookbackDate.setDate(lookbackDate.getDate() - FILTERS.RECEIVED_DAYS_LOOKBACK);
      received.value = receivedRes.data.items.filter((b: AcquisitionBook) => {
        if (!b.purchase_date) return false;
        return new Date(b.purchase_date) >= lookbackDate;
      });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to load acquisitions";
      error.value = message;
    } finally {
      loading.value = false;
    }
  }

  async function acquireBook(bookId: number, payload: AcquirePayload) {
    const response = await api.patch(`/books/${bookId}/acquire`, payload);
    // Move from evaluating to inTransit
    evaluating.value = evaluating.value.filter((b) => b.id !== bookId);
    inTransit.value.unshift(response.data);
    return response.data;
  }

  async function markReceived(bookId: number) {
    const response = await api.patch(`/books/${bookId}/status`, null, {
      params: { status: "ON_HAND" },
    });
    // Move from inTransit to received
    inTransit.value = inTransit.value.filter((b) => b.id !== bookId);
    received.value.unshift(response.data);
    return response.data;
  }

  async function cancelOrder(bookId: number) {
    const response = await api.patch(`/books/${bookId}/status`, null, {
      params: { status: "CANCELED" },
    });
    inTransit.value = inTransit.value.filter((b) => b.id !== bookId);
    return response.data;
  }

  async function deleteEvaluating(bookId: number) {
    await api.delete(`/books/${bookId}`);
    evaluating.value = evaluating.value.filter((b) => b.id !== bookId);
  }

  async function addToWatchlist(payload: WatchlistPayload) {
    const fullPayload = {
      ...payload,
      status: "EVALUATING",
      inventory_type: "PRIMARY",
    };
    const response = await api.post("/books", fullPayload);
    evaluating.value.unshift(response.data);
    return response.data;
  }

  async function updateWatchlistItem(bookId: number, payload: UpdateWatchlistPayload) {
    const response = await api.put(`/books/${bookId}`, payload);
    // Update the item in evaluating list
    const index = evaluating.value.findIndex((b) => b.id === bookId);
    if (index >= 0) {
      evaluating.value[index] = response.data;
    }
    return response.data;
  }

  async function archiveSource(bookId: number) {
    const response = await api.post(`/books/${bookId}/archive-source`);
    // Update the book in the appropriate list
    const updateBook = (list: typeof evaluating.value) => {
      const index = list.findIndex((b) => b.id === bookId);
      if (index >= 0) {
        list[index] = { ...list[index], ...response.data };
      }
    };
    updateBook(evaluating.value);
    updateBook(inTransit.value);
    updateBook(received.value);
    return response.data;
  }

  async function addTracking(bookId: number, payload: TrackingPayload) {
    const response = await api.patch(`/books/${bookId}/tracking`, payload);
    // Update the book in inTransit list
    const index = inTransit.value.findIndex((b) => b.id === bookId);
    if (index >= 0) {
      inTransit.value[index] = response.data;
    }
    return response.data;
  }

  async function refreshTracking(bookId: number) {
    const response = await api.post(`/books/${bookId}/tracking/refresh`);
    // Update the book in inTransit list
    const index = inTransit.value.findIndex((b) => b.id === bookId);
    if (index >= 0) {
      inTransit.value[index] = response.data;
    }
    return response.data;
  }

  async function refreshBook(bookId: number) {
    // Fetch single book and update it in the appropriate list
    const response = await api.get(`/books/${bookId}`);
    const book = response.data;

    // Update in evaluating list
    const evalIndex = evaluating.value.findIndex((b) => b.id === bookId);
    if (evalIndex >= 0) {
      evaluating.value[evalIndex] = book;
      return book;
    }

    // Update in inTransit list
    const transitIndex = inTransit.value.findIndex((b) => b.id === bookId);
    if (transitIndex >= 0) {
      inTransit.value[transitIndex] = book;
      return book;
    }

    // Update in received list
    const receivedIndex = received.value.findIndex((b) => b.id === bookId);
    if (receivedIndex >= 0) {
      received.value[receivedIndex] = book;
      return book;
    }

    return book;
  }

  return {
    // State
    evaluating,
    inTransit,
    received,
    loading,
    error,
    // Computed
    evaluatingCount,
    inTransitCount,
    receivedCount,
    // Actions
    fetchAll,
    acquireBook,
    markReceived,
    cancelOrder,
    deleteEvaluating,
    addToWatchlist,
    updateWatchlistItem,
    archiveSource,
    addTracking,
    refreshTracking,
    refreshBook,
  };
});
