import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useBooksStore } from "../books";

// Mock the API
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/services/api";

describe("books store - generateAnalysis", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("generates analysis with default model", async () => {
    const mockResponse = {
      data: {
        id: 1,
        book_id: 42,
        model_used: "anthropic.claude-sonnet-4-5-20240929",
        full_markdown: "# Test Analysis",
      },
    };
    vi.mocked(api.post).mockResolvedValue(mockResponse);

    const store = useBooksStore();
    const result = await store.generateAnalysis(42);

    expect(api.post).toHaveBeenCalledWith("/books/42/analysis/generate", {
      model: "sonnet",
    });
    expect(result.full_markdown).toBe("# Test Analysis");
  });

  it("generates analysis with opus model", async () => {
    const mockResponse = {
      data: {
        id: 1,
        book_id: 42,
        model_used: "anthropic.claude-opus-4-5-20251101",
        full_markdown: "# Opus Analysis",
      },
    };
    vi.mocked(api.post).mockResolvedValue(mockResponse);

    const store = useBooksStore();
    await store.generateAnalysis(42, "opus");

    expect(api.post).toHaveBeenCalledWith("/books/42/analysis/generate", {
      model: "opus",
    });
  });

  it("updates currentBook.has_analysis on success", async () => {
    const mockResponse = {
      data: {
        id: 1,
        book_id: 42,
        full_markdown: "# Test",
      },
    };
    vi.mocked(api.post).mockResolvedValue(mockResponse);

    const store = useBooksStore();
    store.currentBook = { id: 42, title: "Test", has_analysis: false } as any;

    await store.generateAnalysis(42);

    expect(store.currentBook?.has_analysis).toBe(true);
  });
});
