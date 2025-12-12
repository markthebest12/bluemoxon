import { ref } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";

export interface ImagePreview {
  url: string;
  preview: string; // base64 data URI
  content_type: string;
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
    condition_description?: string;
  };
  images: ImagePreview[];
  image_urls: string[];
  matches: {
    author?: ReferenceMatch;
    binder?: ReferenceMatch;
    publisher?: ReferenceMatch;
  };
}

export const useListingsStore = defineStore("listings", () => {
  // State
  const extracting = ref(false);
  const error = ref<string | null>(null);
  const lastExtraction = ref<ExtractedListing | null>(null);

  // Actions
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
    // Actions
    extractListing,
    clearError,
    clearLastExtraction,
  };
});
