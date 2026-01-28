import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAnalytics } from "../useAnalytics";

describe("useAnalytics", () => {
  beforeEach(() => {
    vi.spyOn(console, "log").mockImplementation(() => {});
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
});
