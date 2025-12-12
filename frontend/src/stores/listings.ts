import { ref } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";

export interface ImagePreview {
  s3_key: string;
  presigned_url: string;
}

export interface ReferenceMatch {
  id: number;
  name: string;
  similarity: number;
}

export interface ExtractedListing {
  ebay_url: string;
  ebay_item_id: string;
  listing_data: {
    title?: string;
    author?: string;
    binder?: string;
    publisher?: string;
    price?: number;
    currency?: string;
    volumes?: number;
    publication_date?: string;
    binding_type?: string;
    binding?: string; // Alternative field name from API
    condition_description?: string;
  };
  images: ImagePreview[];
  image_urls: string[]; // Original eBay image URLs (for reference)
  matches: {
    author?: ReferenceMatch;
    binder?: ReferenceMatch;
    publisher?: ReferenceMatch;
  };
}

// Async extraction types
export type ExtractionStatus = "pending" | "scraped" | "ready" | "error";

export interface AsyncExtractionJob {
  item_id: string;
  status: "started" | "already_scraped";
  message: string;
}

export interface ExtractionStatusResponse {
  item_id: string;
  status: ExtractionStatus;
  ebay_url?: string;
  listing_data?: ExtractedListing["listing_data"];
  images: ImagePreview[];
  matches: ExtractedListing["matches"];
  error?: string;
}

export const useListingsStore = defineStore("listings", () => {
  // State
  const extracting = ref(false);
  const error = ref<string | null>(null);
  const lastExtraction = ref<ExtractedListing | null>(null);

  // Async extraction state
  const activeExtractions = ref<Map<string, ExtractionStatusResponse>>(new Map());
  const extractionPollers = ref<Map<string, ReturnType<typeof setInterval>>>(new Map());

  // Actions - Sync (legacy, kept for compatibility)
  async function extractListing(url: string): Promise<ExtractedListing> {
    extracting.value = true;
    error.value = null;

    try {
      const response = await api.post("/listings/extract", { url });
      lastExtraction.value = response.data;
      return response.data;
    } catch (e: any) {
      // Handle specific error types
      if (e.response?.status === 429) {
        error.value = "Rate limited by eBay. Please try again in a few minutes.";
      } else if (e.response?.status === 502) {
        error.value = "Failed to scrape listing. The page may be unavailable.";
      } else if (e.response?.status === 400) {
        error.value = "Invalid eBay URL. Please check the URL and try again.";
      } else if (e.response?.status === 422) {
        error.value = "Could not extract listing data. The listing format may not be supported.";
      } else {
        error.value = e.response?.data?.detail || e.message || "Failed to extract listing";
      }
      throw e;
    } finally {
      extracting.value = false;
    }
  }

  // Actions - Async extraction (new)

  /**
   * Start async extraction. Returns immediately, poll status for results.
   */
  async function extractListingAsync(url: string): Promise<AsyncExtractionJob> {
    error.value = null;

    try {
      const response = await api.post("/listings/extract-async", { url });
      const job = response.data as AsyncExtractionJob;

      // Initialize tracking with pending status
      activeExtractions.value.set(job.item_id, {
        item_id: job.item_id,
        status: "pending",
        images: [],
        matches: {},
      });

      // Start polling for status
      startExtractionPoller(job.item_id);

      return job;
    } catch (e: any) {
      if (e.response?.status === 400) {
        error.value = "Invalid eBay URL. Please check the URL and try again.";
      } else {
        error.value = e.response?.data?.detail || e.message || "Failed to start extraction";
      }
      throw e;
    }
  }

  /**
   * Poll extraction status for an item.
   */
  async function fetchExtractionStatus(itemId: string): Promise<ExtractionStatusResponse> {
    const response = await api.get(`/listings/extract/${itemId}/status`);
    const status = response.data as ExtractionStatusResponse;

    // Update tracked status
    activeExtractions.value.set(itemId, status);

    return status;
  }

  /**
   * Start polling for extraction status.
   */
  function startExtractionPoller(itemId: string, intervalMs: number = 3000) {
    // Clear existing poller
    stopExtractionPoller(itemId);

    const poller = setInterval(async () => {
      try {
        const status = await fetchExtractionStatus(itemId);

        if (status.status === "ready" || status.status === "error") {
          stopExtractionPoller(itemId);

          // Convert to ExtractedListing format if ready
          if (status.status === "ready" && status.listing_data) {
            lastExtraction.value = {
              ebay_url: status.ebay_url || `https://www.ebay.com/itm/${itemId}`,
              ebay_item_id: itemId,
              listing_data: status.listing_data,
              images: status.images,
              image_urls: [],
              matches: status.matches,
            };
          }
        }
      } catch (e) {
        console.error(`Failed to poll extraction status for ${itemId}:`, e);
        // Don't stop on error, keep trying
      }
    }, intervalMs);

    extractionPollers.value.set(itemId, poller);
  }

  /**
   * Stop polling for an item.
   */
  function stopExtractionPoller(itemId: string) {
    const existingPoller = extractionPollers.value.get(itemId);
    if (existingPoller) {
      clearInterval(existingPoller);
      extractionPollers.value.delete(itemId);
    }
  }

  /**
   * Get active extraction for an item.
   */
  function getActiveExtraction(itemId: string): ExtractionStatusResponse | undefined {
    return activeExtractions.value.get(itemId);
  }

  /**
   * Check if extraction is in progress (pending or scraped).
   */
  function isExtractionInProgress(itemId: string): boolean {
    const status = activeExtractions.value.get(itemId);
    return !!status && (status.status === "pending" || status.status === "scraped");
  }

  /**
   * Clear completed extraction from tracking.
   */
  function clearExtraction(itemId: string) {
    activeExtractions.value.delete(itemId);
    stopExtractionPoller(itemId);
  }

  function clearError() {
    error.value = null;
  }

  function clearLastExtraction() {
    lastExtraction.value = null;
  }

  return {
    // State
    extracting,
    error,
    lastExtraction,
    activeExtractions,
    // Actions - Sync
    extractListing,
    // Actions - Async
    extractListingAsync,
    fetchExtractionStatus,
    getActiveExtraction,
    isExtractionInProgress,
    clearExtraction,
    // Utilities
    clearError,
    clearLastExtraction,
  };
});
