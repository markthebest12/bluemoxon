/**
 * Cytoscape E2E Test Utilities
 *
 * Helpers for interacting with Cytoscape graph instances in Playwright tests.
 * Accesses Cytoscape via its internal `_cyreg` property (set at core/index.mjs:43).
 * This is NOT a public Cytoscape API -- if a Cytoscape upgrade breaks it,
 * update these helpers.
 *
 * Each helper uses `page.evaluate()` / `page.evaluateHandle()` which runs in
 * the browser context, so the graph container selector is inlined in every
 * callback (imported constants cannot cross the serialization boundary).
 */

import type { JSHandle, Page } from "@playwright/test";

/**
 * Return a JSHandle to the live Cytoscape core instance.
 *
 * The handle can be passed to subsequent `page.evaluate()` calls to avoid
 * repeating the container-lookup + `_cyreg` boilerplate.
 *
 * @example
 * ```ts
 * const cy = await getCytoscapeInstance(page);
 * const count = await page.evaluate((c) => c?.nodes().length ?? 0, cy);
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function getCytoscapeInstance(page: Page): Promise<JSHandle<any>> {
  return page.evaluateHandle(() => {
    const container = document.querySelector(
      "[data-testid='network-graph']",
    ) as HTMLElement | null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (container as any)?._cyreg?.cy;
  });
}

/**
 * Return the number of visible Cytoscape nodes.
 */
export async function getNodeCount(page: Page): Promise<number> {
  return page.evaluate(() => {
    const container = document.querySelector(
      "[data-testid='network-graph']",
    ) as HTMLElement | null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = (container as any)?._cyreg?.cy;
    return cy ? (cy.nodes().length as number) : 0;
  });
}

/**
 * Emit a Cytoscape `tap` event on the node identified by {@link nodeId}.
 *
 * Uses a synthetic event rather than coordinate-based `mouse.click()` to avoid
 * sub-pixel offset mismatches between Cytoscape's canvas coordinates and the
 * DOM bounding box.
 *
 * NOTE: The emitted event lacks position / mouse properties that a real user
 * tap would include, so this tests the data pipeline but not the full
 * interaction path.
 */
export async function tapNode(page: Page, nodeId: string): Promise<void> {
  await page.evaluate((id: string) => {
    const container = document.querySelector(
      "[data-testid='network-graph']",
    ) as HTMLElement | null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = (container as any)?._cyreg?.cy;
    if (!cy) return;
    const node = cy.getElementById(id);
    if (node && node.length > 0) {
      node.emit("tap");
    }
  }, nodeId);
}

/**
 * Wait for the Cytoscape layout to finish animating with at least one node.
 */
export async function waitForLayoutSettled(page: Page): Promise<void> {
  await page.waitForFunction(
    () => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      return cy && cy.nodes().length > 0 && !cy.animated();
    },
    { timeout: 10000 },
  );
}

/**
 * Wait until the node count exceeds {@link threshold} and the layout is no
 * longer animating.
 */
export async function waitForNodeCountAbove(
  page: Page,
  threshold: number,
): Promise<void> {
  await page.waitForFunction(
    (expected: number) => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      return cy && cy.nodes().length > expected && !cy.animated();
    },
    threshold,
    { timeout: 10000 },
  );
}
