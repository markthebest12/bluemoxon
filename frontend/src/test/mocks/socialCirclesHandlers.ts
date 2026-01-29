/**
 * MSW (Mock Service Worker) handlers for Social Circles API.
 *
 * These handlers intercept HTTP requests during tests and return mock data.
 * Use these to test components that make API calls without hitting real endpoints.
 *
 * Usage:
 * ```ts
 * import { setupServer } from 'msw/node';
 * import { socialCirclesHandlers } from '@/test/mocks/socialCirclesHandlers';
 *
 * const server = setupServer(...socialCirclesHandlers);
 *
 * beforeAll(() => server.listen());
 * afterEach(() => server.resetHandlers());
 * afterAll(() => server.close());
 * ```
 */

import { http, HttpResponse, delay } from "msw";
import {
  mockResponse,
  mockResponseEmpty,
  mockResponseTruncated,
  mockMeta,
} from "../fixtures/socialCircles";
import type { SocialCirclesResponse } from "@/types/socialCircles";

// Base API URL pattern (matches both relative and absolute URLs)
const API_BASE = "*/api/v1";

// =============================================================================
// Default Handlers
// =============================================================================

/**
 * Default handlers that return successful responses with mock data.
 */
export const socialCirclesHandlers = [
  // GET /api/v1/social-circles/
  http.get(`${API_BASE}/social-circles/`, ({ request }) => {
    const url = new URL(request.url);

    // Support query parameter variations
    const includeBinders = url.searchParams.get("include_binders") !== "false";
    const minBookCount = parseInt(url.searchParams.get("min_book_count") || "1", 10);
    const eraFilter = url.searchParams.getAll("era");

    // Filter nodes based on query params
    let nodes = [...mockResponse.nodes];

    if (!includeBinders) {
      nodes = nodes.filter((n) => n.type !== "binder");
    }

    if (minBookCount > 1) {
      nodes = nodes.filter((n) => n.book_count >= minBookCount);
    }

    if (eraFilter.length > 0) {
      nodes = nodes.filter((n) => !n.era || eraFilter.includes(n.era));
    }

    // Filter edges to only include those where both nodes exist
    const nodeIds = new Set(nodes.map((n) => n.id));
    const edges = mockResponse.edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));

    const response: SocialCirclesResponse = {
      nodes,
      edges,
      meta: {
        ...mockMeta,
        total_authors: nodes.filter((n) => n.type === "author").length,
        total_publishers: nodes.filter((n) => n.type === "publisher").length,
        total_binders: nodes.filter((n) => n.type === "binder").length,
      },
    };

    return HttpResponse.json(response);
  }),

  // GET /api/v1/social-circles/health
  http.get(`${API_BASE}/social-circles/health`, () => {
    return HttpResponse.json({
      status: "healthy",
      latency_ms: 150.25,
      checks: {
        node_counts: {
          status: "healthy",
          authors: 5,
          publishers: 3,
          binders: 3,
        },
        edge_counts: {
          status: "healthy",
          publisher: 2,
          shared_publisher: 2,
          binder: 1,
        },
        query_performance: {
          status: "healthy",
          build_time_ms: 150.25,
          threshold_ms: 500,
        },
      },
    });
  }),
];

// =============================================================================
// Specialized Handlers for Different Scenarios
// =============================================================================

/**
 * Handler that returns an empty response (no data).
 */
export const emptyDataHandler = http.get(`${API_BASE}/social-circles/`, () => {
  return HttpResponse.json(mockResponseEmpty);
});

/**
 * Handler that returns a truncated response.
 */
export const truncatedDataHandler = http.get(`${API_BASE}/social-circles/`, () => {
  return HttpResponse.json(mockResponseTruncated);
});

/**
 * Handler that simulates network error.
 */
export const networkErrorHandler = http.get(`${API_BASE}/social-circles/`, () => {
  return HttpResponse.error();
});

/**
 * Handler that returns 500 Internal Server Error.
 */
export const serverErrorHandler = http.get(`${API_BASE}/social-circles/`, () => {
  return new HttpResponse(JSON.stringify({ error: "Internal Server Error" }), {
    status: 500,
    headers: { "Content-Type": "application/json" },
  });
});

/**
 * Handler that returns 401 Unauthorized.
 */
export const unauthorizedHandler = http.get(`${API_BASE}/social-circles/`, () => {
  return new HttpResponse(JSON.stringify({ detail: "Not authenticated" }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
});

/**
 * Handler that simulates slow response (2 second delay).
 */
export const slowResponseHandler = http.get(`${API_BASE}/social-circles/`, async () => {
  await delay(2000);
  return HttpResponse.json(mockResponse);
});

/**
 * Handler that returns degraded health status.
 */
export const degradedHealthHandler = http.get(`${API_BASE}/social-circles/health`, () => {
  return HttpResponse.json({
    status: "degraded",
    latency_ms: 750.5,
    checks: {
      node_counts: {
        status: "healthy",
        authors: 5,
        publishers: 3,
        binders: 3,
      },
      edge_counts: {
        status: "healthy",
        publisher: 2,
        shared_publisher: 2,
        binder: 1,
      },
      query_performance: {
        status: "degraded",
        build_time_ms: 750.5,
        threshold_ms: 500,
      },
    },
  });
});

/**
 * Handler that returns unhealthy status.
 */
export const unhealthyHandler = http.get(`${API_BASE}/social-circles/health`, () => {
  return HttpResponse.json({
    status: "unhealthy",
    error: "Database connection failed",
    latency_ms: 5000,
  });
});

// =============================================================================
// Handler Factory Functions
// =============================================================================

/**
 * Create a handler that returns a custom response.
 */
export function createCustomResponseHandler(response: SocialCirclesResponse) {
  return http.get(`${API_BASE}/social-circles/`, () => {
    return HttpResponse.json(response);
  });
}

/**
 * Create a handler with custom delay.
 */
export function createDelayedHandler(delayMs: number) {
  return http.get(`${API_BASE}/social-circles/`, async () => {
    await delay(delayMs);
    return HttpResponse.json(mockResponse);
  });
}

/**
 * Create a handler that calls a callback for each request.
 * Useful for tracking requests in tests.
 */
export function createTrackingHandler(callback: (url: URL) => void) {
  return http.get(`${API_BASE}/social-circles/`, ({ request }) => {
    callback(new URL(request.url));
    return HttpResponse.json(mockResponse);
  });
}
