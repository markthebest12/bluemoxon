import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAnalytics, _resetAnalyticsForTesting } from "../useAnalytics";

describe("useAnalytics", () => {
  beforeEach(() => {
    _resetAnalyticsForTesting();
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  it("trackEvent logs in dev mode", () => {
    const { trackEvent } = useAnalytics();
    trackEvent({ event: "test_event", properties: { foo: "bar" } });
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "test_event", { foo: "bar" });
  });

  it("trackNodeSelect creates correct event", () => {
    const { trackNodeSelect } = useAnalytics();
    const mockNode = { id: "1", name: "Test", type: "author" } as Parameters<
      ReturnType<typeof useAnalytics>["trackNodeSelect"]
    >[0];
    trackNodeSelect(mockNode);
    expect(console.log).toHaveBeenCalledWith(
      "[Analytics]",
      "node_selected",
      expect.objectContaining({ nodeId: "1", nodeType: "author" })
    );
  });

  it("trackEdgeSelect creates correct event", () => {
    const { trackEdgeSelect } = useAnalytics();
    const mockEdge = { source: "1", target: "2" } as Parameters<
      ReturnType<typeof useAnalytics>["trackEdgeSelect"]
    >[0];
    trackEdgeSelect(mockEdge);
    expect(console.log).toHaveBeenCalledWith(
      "[Analytics]",
      "edge_selected",
      expect.objectContaining({ source: "1", target: "2" })
    );
  });

  it("trackFilterChange creates correct event", () => {
    const { trackFilterChange } = useAnalytics();
    trackFilterChange("showAuthors", true);
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "filter_changed", {
      filter: "showAuthors",
      value: true,
    });
  });

  it("trackLayoutChange creates correct event", () => {
    const { trackLayoutChange } = useAnalytics();
    trackLayoutChange("circle");
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "layout_changed", { mode: "circle" });
  });

  it("trackSearch creates correct event", () => {
    const { trackSearch } = useAnalytics();
    trackSearch("byron", 5);
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "search_performed", {
      query: "byron",
      resultCount: 5,
    });
  });

  it("trackExport creates correct event", () => {
    const { trackExport } = useAnalytics();
    trackExport("png");
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "graph_exported", { format: "png" });
  });

  it("trackFilterRemove creates correct event", () => {
    const { trackFilterRemove } = useAnalytics();
    trackFilterRemove("showAuthors", true);
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "filter_removed", {
      filter: "showAuthors",
      previousValue: true,
    });
  });

  it("trackFilterReset creates correct event", () => {
    const { trackFilterReset } = useAnalytics();
    trackFilterReset();
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "filters_reset", {});
  });

  it("returns the same singleton instance across multiple calls", () => {
    const instance1 = useAnalytics();
    const instance2 = useAnalytics();
    expect(instance1).toBe(instance2);
  });

  it("returns a fresh instance after reset", () => {
    const instance1 = useAnalytics();
    _resetAnalyticsForTesting();
    const instance2 = useAnalytics();
    expect(instance1).not.toBe(instance2);
  });

  // =========================================================================
  // Entity Profile tracking events
  // =========================================================================

  it("trackProfileViewed creates correct event", () => {
    const { trackProfileViewed } = useAnalytics();
    trackProfileViewed("author", 42, "TIER_1");
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "profile_viewed", {
      entityType: "author",
      entityId: 42,
      tier: "TIER_1",
    });
  });

  it("trackProfileViewed handles null tier", () => {
    const { trackProfileViewed } = useAnalytics();
    trackProfileViewed("publisher", 7, null);
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "profile_viewed", {
      entityType: "publisher",
      entityId: 7,
      tier: null,
    });
  });

  it("trackConnectionClicked creates correct event", () => {
    const { trackConnectionClicked } = useAnalytics();
    trackConnectionClicked("co_author", 99, "Lord Byron");
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "connection_clicked", {
      connectionType: "co_author",
      entityId: 99,
      entityName: "Lord Byron",
    });
  });

  it("trackGossipExpanded creates correct event", () => {
    const { trackGossipExpanded } = useAnalytics();
    trackGossipExpanded(12, "Mary Shelley");
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "gossip_expanded", {
      entityId: 12,
      entityName: "Mary Shelley",
    });
  });

  it("trackBookClicked creates correct event", () => {
    const { trackBookClicked } = useAnalytics();
    trackBookClicked(55, "Frankenstein");
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "book_clicked", {
      bookId: 55,
      bookTitle: "Frankenstein",
    });
  });

  it("trackProfileRegenerated creates correct event", () => {
    const { trackProfileRegenerated } = useAnalytics();
    trackProfileRegenerated("author", 42);
    expect(console.log).toHaveBeenCalledWith("[Analytics]", "profile_regenerated", {
      entityType: "author",
      entityId: 42,
    });
  });

  it("logs errors in dev mode and does not throw", () => {
    // Mock console.log to throw an error
    vi.spyOn(console, "log").mockImplementation(() => {
      throw new Error("Test error");
    });

    const { trackEvent } = useAnalytics();

    // Should not throw - the error should be caught
    expect(() => {
      trackEvent({ event: "test_event", properties: { foo: "bar" } });
    }).not.toThrow();

    // Should warn in dev mode
    expect(console.warn).toHaveBeenCalledWith(
      "[Analytics] Error tracking event:",
      expect.any(Error)
    );
  });
});
