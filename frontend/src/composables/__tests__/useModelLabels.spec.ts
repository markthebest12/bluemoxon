import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/services/api";
import { _resetModelLabelsCache } from "../useModelLabels";

describe("useModelLabels", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _resetModelLabelsCache();
  });

  it("fetches labels from the public API on first use", async () => {
    const mockLabels = { sonnet: "Sonnet 4.5", opus: "Opus 4.6", haiku: "Haiku 3.5" };
    vi.mocked(api.get).mockResolvedValueOnce({ data: { labels: mockLabels } });

    const { useModelLabels } = await import("../useModelLabels");
    const { labels, loaded } = useModelLabels();

    // Wait for the async fetch to resolve
    await vi.waitFor(() => expect(loaded.value).toBe(true));

    expect(api.get).toHaveBeenCalledWith("/config/model-labels");
    expect(labels.value).toEqual(mockLabels);
  });

  it("shares cached result across multiple calls", async () => {
    const mockLabels = { sonnet: "Sonnet 4.5", opus: "Opus 4.6", haiku: "Haiku 3.5" };
    vi.mocked(api.get).mockResolvedValueOnce({ data: { labels: mockLabels } });

    const { useModelLabels } = await import("../useModelLabels");

    const first = useModelLabels();
    const second = useModelLabels();

    await vi.waitFor(() => expect(first.loaded.value).toBe(true));

    // Should only fetch once
    expect(api.get).toHaveBeenCalledTimes(1);
    // Both should share the same reactive ref
    expect(second.labels.value).toEqual(mockLabels);
  });

  it("provides fallback labels on API error", async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

    const { useModelLabels } = await import("../useModelLabels");
    const { labels, error } = useModelLabels();

    await vi.waitFor(() => expect(error.value).toBe("Failed to load model labels"));

    // Fallback labels should be set
    expect(labels.value).toHaveProperty("sonnet");
    expect(labels.value).toHaveProperty("opus");
    expect(labels.value).toHaveProperty("haiku");
  });

  describe("formatModelId", () => {
    it("formats versioned model IDs", async () => {
      const mockLabels = { sonnet: "Sonnet 4.5", opus: "Opus 4.6", haiku: "Haiku 3.5" };
      vi.mocked(api.get).mockResolvedValueOnce({ data: { labels: mockLabels } });

      const { useModelLabels } = await import("../useModelLabels");
      const { formatModelId } = useModelLabels();

      await vi.waitFor(() =>
        expect(formatModelId("us.anthropic.claude-sonnet-4-5-20250929-v1:0")).toBe(
          "Claude Sonnet 4.5"
        )
      );
    });

    it("formats legacy model IDs", async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: { labels: {} } });

      const { useModelLabels } = await import("../useModelLabels");
      const { formatModelId } = useModelLabels();

      expect(formatModelId("claude-3-5-sonnet-20241022")).toBe("Claude 3.5 Sonnet");
    });

    it("uses registry labels for key lookups", async () => {
      const mockLabels = { opus: "Opus 4.6" };
      vi.mocked(api.get).mockResolvedValueOnce({ data: { labels: mockLabels } });

      const { useModelLabels } = await import("../useModelLabels");
      const { formatModelId, loaded } = useModelLabels();

      await vi.waitFor(() => expect(loaded.value).toBe(true));

      expect(formatModelId("opus")).toBe("Claude Opus 4.6");
    });

    it("falls back for unknown model IDs", async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: { labels: {} } });

      const { useModelLabels } = await import("../useModelLabels");
      const { formatModelId } = useModelLabels();

      expect(formatModelId("some.unknown.opus.model")).toBe("Claude Opus");
      expect(formatModelId("fully.unknown.model")).toBe("model");
    });
  });
});
