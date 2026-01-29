// frontend/src/composables/socialcircles/useAnalytics.ts

/**
 * Composable for tracking user interactions in Social Circles.
 * Development mode logs to console; production mode stubs for future analytics service.
 * All tracking is non-blocking to prevent UI disruptions.
 */

import type { ApiNode, ApiEdge, LayoutMode } from "@/types/socialCircles";

// =============================================================================
// Types
// =============================================================================

export interface AnalyticsEvent {
  event: string;
  properties?: Record<string, unknown>;
}

export type ExportFormat = "png" | "json" | "url";

// =============================================================================
// Singleton instance cache
// =============================================================================

let _instance: ReturnType<typeof _createAnalytics> | null = null;

/** Reset singleton for testing. Guarded to only run in test mode. */
export function _resetAnalyticsForTesting(): void {
  if (import.meta.env.MODE === "test") {
    _instance = null;
  }
}

// =============================================================================
// Composable
// =============================================================================

/**
 * Returns a singleton analytics instance. Multiple calls to useAnalytics()
 * return the same object, preventing duplicate event tracking when the
 * composable is used in more than one component.
 */
export function useAnalytics() {
  if (!_instance) {
    _instance = _createAnalytics();
  }
  return _instance;
}

function _createAnalytics() {
  const isDev = import.meta.env.DEV;

  /**
   * Track a generic analytics event.
   * Non-blocking: errors are silently caught to prevent UI disruption.
   */
  function trackEvent(event: AnalyticsEvent): void {
    try {
      if (isDev) {
        console.log("[Analytics]", event.event, event.properties);
      }
      // Future: send to analytics service
      // analyticsService.track(event);
    } catch {
      // Silently ignore errors to prevent UI disruption
    }
  }

  /**
   * Track when a node is selected in the graph.
   */
  function trackNodeSelect(node: ApiNode): void {
    trackEvent({
      event: "node_selected",
      properties: {
        nodeId: node.id,
        nodeType: node.type,
        nodeName: node.name,
      },
    });
  }

  /**
   * Track when an edge is selected in the graph.
   */
  function trackEdgeSelect(edge: ApiEdge): void {
    trackEvent({
      event: "edge_selected",
      properties: {
        source: edge.source,
        target: edge.target,
        edgeType: edge.type,
      },
    });
  }

  /**
   * Track when a filter value changes.
   */
  function trackFilterChange(filter: string, value: unknown): void {
    trackEvent({
      event: "filter_changed",
      properties: {
        filter,
        value,
      },
    });
  }

  /**
   * Track when the graph layout mode changes.
   */
  function trackLayoutChange(mode: LayoutMode): void {
    trackEvent({
      event: "layout_changed",
      properties: {
        mode,
      },
    });
  }

  /**
   * Track when a search is performed.
   */
  function trackSearch(query: string, resultCount: number): void {
    trackEvent({
      event: "search_performed",
      properties: {
        query,
        resultCount,
      },
    });
  }

  /**
   * Track when the graph is exported.
   */
  function trackExport(format: ExportFormat): void {
    trackEvent({
      event: "graph_exported",
      properties: {
        format,
      },
    });
  }

  return {
    trackEvent,
    trackNodeSelect,
    trackEdgeSelect,
    trackFilterChange,
    trackLayoutChange,
    trackSearch,
    trackExport,
  };
}
