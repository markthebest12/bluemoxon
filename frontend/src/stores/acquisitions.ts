import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";

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
  scoring_snapshot?: Record<string, unknown>;
  primary_image_url?: string;
  has_analysis?: boolean;
  investment_grade?: number | null;
  strategic_fit?: number | null;
  collection_impact?: number | null;
  overall_score?: number | null;
  scores_calculated_at?: string | null;
  volumes?: number;
  is_complete?: boolean;
  source_url?: string;
}

export interface AcquirePayload {
  purchase_price: number;
  purchase_date: string;
  order_number: string;
  place_of_purchase: string;
  estimated_delivery?: string;
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
            status: "EVALUATING",
            inventory_type: "PRIMARY",
            per_page: 100,
          },
        }),
        api.get("/books", {
          params: {
            status: "IN_TRANSIT",
            inventory_type: "PRIMARY",
            per_page: 100,
          },
        }),
        api.get("/books", {
          params: {
            status: "ON_HAND",
            inventory_type: "PRIMARY",
            per_page: 50,
            sort_by: "purchase_date",
            sort_order: "desc",
          },
        }),
      ]);

      evaluating.value = evalRes.data.items;
      inTransit.value = transitRes.data.items;

      // Only show last 30 days of received items
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      received.value = receivedRes.data.items.filter((b: AcquisitionBook) => {
        if (!b.purchase_date) return false;
        return new Date(b.purchase_date) >= thirtyDaysAgo;
      });
    } catch (e: any) {
      error.value = e.message || "Failed to load acquisitions";
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
  };
});
