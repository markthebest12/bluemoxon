import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/services/api";

export interface ScoreBreakdownItem {
  points: number;
  notes: string;
}

export interface FMVComparable {
  title: string;
  price: number;
  condition?: string;
  days_ago?: number;
}

export interface EvalRunbook {
  id: number;
  book_id: number;
  total_score: number;
  score_breakdown: Record<string, ScoreBreakdownItem>;
  recommendation: "PASS" | "ACQUIRE";
  original_asking_price?: number;
  current_asking_price?: number;
  discount_code?: string;
  price_notes?: string;
  fmv_low?: number;
  fmv_high?: number;
  recommended_price?: number;
  ebay_comparables?: FMVComparable[];
  abebooks_comparables?: FMVComparable[];
  condition_grade?: string;
  condition_positives?: string[];
  condition_negatives?: string[];
  critical_issues?: string[];
  analysis_narrative?: string;
  item_identification?: Record<string, string>;
  generated_at: string;
  created_at: string;
  updated_at: string;

  // Tiered recommendation fields
  recommendation_tier?: "STRONG_BUY" | "BUY" | "CONDITIONAL" | "PASS";
  quality_score?: number;
  strategic_fit_score?: number;
  combined_score?: number;
  price_position?: "EXCELLENT" | "GOOD" | "FAIR" | "POOR";
  suggested_offer?: number;
  recommendation_reasoning?: string;
  strategic_floor_applied?: boolean;
  quality_floor_applied?: boolean;
  scoring_version?: string;
  score_source?: "eval_runbook" | "napoleon";
  last_scored_price?: number;

  // Napoleon override fields
  napoleon_recommendation?: string;
  napoleon_reasoning?: string;
  napoleon_analyzed_at?: string;
}

export interface PriceUpdatePayload {
  new_price: number;
  discount_code?: string;
  notes?: string;
}

export interface PriceUpdateResponse {
  previous_price?: number;
  new_price: number;
  score_before: number;
  score_after: number;
  recommendation_before: string;
  recommendation_after: string;
  runbook: EvalRunbook;
}

export interface PriceHistoryEntry {
  id: number;
  previous_price?: number;
  new_price?: number;
  discount_code?: string;
  notes?: string;
  score_before?: number;
  score_after?: number;
  changed_at: string;
}

export interface RefreshResponse {
  status: "completed" | "failed";
  score_before?: number;
  score_after: number;
  message: string;
  runbook: EvalRunbook;
}

export const useEvalRunbookStore = defineStore("evalRunbook", () => {
  const currentRunbook = ref<EvalRunbook | null>(null);
  const priceHistory = ref<PriceHistoryEntry[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchRunbook(bookId: number): Promise<EvalRunbook | null> {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get(`/books/${bookId}/eval-runbook`);
      currentRunbook.value = response.data;
      return response.data;
    } catch (e: unknown) {
      const err = e as { response?: { status?: number }; message?: string };
      if (err.response?.status === 404) {
        currentRunbook.value = null;
        return null;
      }
      error.value = err.message || "Failed to fetch eval runbook";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updatePrice(
    bookId: number,
    payload: PriceUpdatePayload
  ): Promise<PriceUpdateResponse> {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.patch(`/books/${bookId}/eval-runbook/price`, payload);
      currentRunbook.value = response.data.runbook;
      return response.data;
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to update price";
      error.value = message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchPriceHistory(bookId: number): Promise<PriceHistoryEntry[]> {
    try {
      const response = await api.get(`/books/${bookId}/eval-runbook/history`);
      priceHistory.value = response.data;
      return response.data;
    } catch (e: unknown) {
      console.error("Failed to fetch price history:", e);
      return [];
    }
  }

  async function refreshRunbook(bookId: number): Promise<RefreshResponse> {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.post(`/books/${bookId}/eval-runbook/refresh`);
      currentRunbook.value = response.data.runbook;
      return response.data;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      error.value = err.response?.data?.detail || err.message || "Failed to refresh analysis";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function clearRunbook() {
    currentRunbook.value = null;
    priceHistory.value = [];
    error.value = null;
  }

  return {
    currentRunbook,
    priceHistory,
    loading,
    error,
    fetchRunbook,
    updatePrice,
    fetchPriceHistory,
    refreshRunbook,
    clearRunbook,
  };
});
