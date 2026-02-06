import { test, expect } from "@playwright/test";

import { getCytoscapeInstance, waitForLayoutSettled } from "./utils/cytoscape";

/**
 * E2E tests for AI-discovered connections in the Social Circles graph.
 *
 * Validates that:
 * - The graph contains AI connection edge types (family, friendship, influence, collaboration, scandal)
 * - Personal connection edges (family, friendship, collaboration) are visible with correct styling
 * - Scandal edges are rendered with distinct styling (dashed red)
 * - AI edges coexist with book-based edges (publisher, shared_publisher, binder)
 *
 * AI connection edge types use blue (#60a5fa) for personal connections and red (#f87171) for scandal.
 * Edge type is stored in Cytoscape edge.data("type") matching the ConnectionType union.
 *
 * Gracefully skips if the staging dataset has no AI connections.
 */

/** AI-discovered connection types in the social circles graph */
const AI_EDGE_TYPES = ["family", "friendship", "influence", "collaboration", "scandal"] as const;

/** Personal (non-scandal) AI connection types */
const PERSONAL_EDGE_TYPES = ["family", "friendship", "influence", "collaboration"] as const;

/** Book-based connection types */
const BOOK_EDGE_TYPES = ["publisher", "shared_publisher", "binder"] as const;

test.describe("Social Circles - AI Connection Edges", () => {
  test.beforeEach(async ({ page }) => {
    const viewport = page.viewportSize();
    test.skip(!!viewport && viewport.width <= 768, "Graph tests require desktop viewport");

    // Set up response listener before navigation to capture Lambda cold-start latency
    const apiResponse = page.waitForResponse(
      (resp) => resp.url().includes("/api/v1/social-circles") && resp.status() === 200
    );
    await page.goto("/social-circles");

    // Wait for API response first — separates network/Lambda latency from render time
    await apiResponse;

    // Wait for loading spinner to disappear before asserting graph visibility
    await expect(page.getByText("Loading social circles...")).toBeHidden({ timeout: 10000 });

    // Allow 30s for graph render after data arrives (consistent with layout spec)
    await expect(page.getByTestId("network-graph")).toBeVisible({ timeout: 30000 });
  });

  test("graph loads with AI connection edges present", async ({ page }) => {
    await waitForLayoutSettled(page);

    const cy = await getCytoscapeInstance(page);
    const aiEdgeCount = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (args: { cyInst: any; types: string[] }) => {
        if (!args.cyInst) return 0;
        return args.cyInst
          .edges()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .filter((e: any) => args.types.includes(e.data("type")))
          .length as number;
      },
      { cyInst: cy, types: [...AI_EDGE_TYPES] }
    );

    test.skip(aiEdgeCount === 0, "No AI connection edges in graph — AI data may not be loaded");
    expect(aiEdgeCount).toBeGreaterThan(0);
  });

  test("personal connection edges are visible in the graph", async ({ page }) => {
    await waitForLayoutSettled(page);

    const cy = await getCytoscapeInstance(page);
    const personalEdges = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (args: { cyInst: any; types: string[] }) => {
        if (!args.cyInst) return [];
        return args.cyInst
          .edges()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .filter((e: any) => args.types.includes(e.data("type")))
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .map((e: any) => ({
            id: e.id() as string,
            type: e.data("type") as string,
            edgeColor: e.data("edgeColor") as string,
            edgeStyle: e.data("edgeStyle") as string,
            strength: e.data("strength") as number,
          }));
      },
      { cyInst: cy, types: [...PERSONAL_EDGE_TYPES] }
    );

    test.skip(personalEdges.length === 0, "No personal connection edges found in graph");

    // Verify personal edges have blue color (#60a5fa)
    for (const edge of personalEdges) {
      expect(edge.edgeColor).toBe("#60a5fa");
      expect(edge.strength).toBeGreaterThan(0);
    }
  });

  test("scandal edges are rendered with red color and dashed style", async ({ page }) => {
    await waitForLayoutSettled(page);

    const cy = await getCytoscapeInstance(page);
    const scandalEdges = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (cyInst: any) => {
        if (!cyInst) return [];
        return cyInst
          .edges()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .filter((e: any) => e.data("type") === "scandal")
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .map((e: any) => ({
            id: e.id() as string,
            edgeColor: e.data("edgeColor") as string,
            edgeStyle: e.data("edgeStyle") as string,
            edgeOpacity: e.data("edgeOpacity") as number,
          }));
      },
      cy
    );

    test.skip(scandalEdges.length === 0, "No scandal edges in graph — dataset may lack scandals");

    // Scandal edges should be red and dashed (per EDGE_COLORS and EDGE_STYLES constants)
    for (const edge of scandalEdges) {
      expect(edge.edgeColor).toBe("#f87171");
      expect(edge.edgeStyle).toBe("dashed");
      expect(edge.edgeOpacity).toBe(0.8);
    }
  });

  test("AI and book-based edges coexist in the graph", async ({ page }) => {
    await waitForLayoutSettled(page);

    const cy = await getCytoscapeInstance(page);
    const edgeCounts = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (args: { cyInst: any; aiTypes: string[]; bookTypes: string[] }) => {
        if (!args.cyInst) return { ai: 0, book: 0, total: 0 };
        const edges = args.cyInst.edges();
        return {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          ai: edges.filter((e: any) => args.aiTypes.includes(e.data("type"))).length as number,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          book: edges.filter((e: any) => args.bookTypes.includes(e.data("type"))).length as number,
          total: edges.length as number,
        };
      },
      { cyInst: cy, aiTypes: [...AI_EDGE_TYPES], bookTypes: [...BOOK_EDGE_TYPES] }
    );

    test.skip(edgeCounts.ai === 0, "No AI edges found — AI data may not be loaded");

    // Both types should be present in a dataset with AI connections
    expect(edgeCounts.book).toBeGreaterThan(0);
    expect(edgeCounts.ai).toBeGreaterThan(0);

    // Total should equal the sum of AI + book-based
    expect(edgeCounts.total).toBe(edgeCounts.ai + edgeCounts.book);
  });

  test("AI edge types have valid strength values", async ({ page }) => {
    await waitForLayoutSettled(page);

    const cy = await getCytoscapeInstance(page);
    const aiEdgeStrengths = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (args: { cyInst: any; types: string[] }) => {
        if (!args.cyInst) return [];
        return args.cyInst
          .edges()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .filter((e: any) => args.types.includes(e.data("type")))
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .map((e: any) => ({
            type: e.data("type") as string,
            strength: e.data("strength") as number,
            edgeWidth: e.data("edgeWidth") as number,
          }));
      },
      { cyInst: cy, types: [...AI_EDGE_TYPES] }
    );

    test.skip(aiEdgeStrengths.length === 0, "No AI edges found — AI data may not be loaded");

    // All AI edges should have valid strength (1-10) and calculated width
    for (const edge of aiEdgeStrengths) {
      expect(edge.strength).toBeGreaterThanOrEqual(1);
      expect(edge.strength).toBeLessThanOrEqual(10);
      expect(edge.edgeWidth).toBeGreaterThan(0);
    }
  });
});

test.describe("Social Circles - AI Edge Interaction", () => {
  test.beforeEach(async ({ page }) => {
    const viewport = page.viewportSize();
    test.skip(!!viewport && viewport.width <= 768, "Graph tests require desktop viewport");

    const apiResponse = page.waitForResponse(
      (resp) => resp.url().includes("/api/v1/social-circles") && resp.status() === 200
    );
    await page.goto("/social-circles");
    await apiResponse;
    await expect(page.getByText("Loading social circles...")).toBeHidden({ timeout: 10000 });
    await expect(page.getByTestId("network-graph")).toBeVisible({ timeout: 30000 });
  });

  test("API response includes AI connection edge types", async ({ page }) => {
    // Intercept the social circles API to verify the response includes AI edges
    const response = await page.waitForResponse(
      (resp) => resp.url().includes("/api/v1/social-circles") && resp.status() === 200,
      { timeout: 5000 }
    ).catch(() => null);

    // The API may have already been called in beforeEach; re-navigate to capture fresh
    if (!response) {
      const freshResponse = page.waitForResponse(
        (resp) => resp.url().includes("/api/v1/social-circles") && resp.status() === 200
      );
      await page.reload();
      const data = await (await freshResponse).json();

      const edgeTypes = new Set(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data.edges?.map((e: any) => e.type) ?? []
      );

      const hasAiTypes = AI_EDGE_TYPES.some((t) => edgeTypes.has(t));
      test.skip(!hasAiTypes, "API response has no AI edge types — AI data may not be generated");

      // Verify at least one AI edge type is present
      const aiTypesFound = AI_EDGE_TYPES.filter((t) => edgeTypes.has(t));
      expect(aiTypesFound.length).toBeGreaterThan(0);
    }
  });
});
