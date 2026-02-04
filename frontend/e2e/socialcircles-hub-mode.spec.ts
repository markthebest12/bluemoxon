import { test, expect } from "@playwright/test";

import {
  getCytoscapeInstance,
  getNodeCount,
  tapNode,
  waitForLayoutSettled,
  waitForNodeCountAbove,
} from "./utils/cytoscape";

/**
 * Social Circles Hub Mode E2E Tests
 *
 * Tests progressive disclosure: initial compact view (25 nodes),
 * ShowMoreButton expansion, and full graph reveal.
 */

test.describe("Social Circles Hub Mode", () => {
  test.beforeEach(async ({ page }) => {
    const viewport = page.viewportSize();
    test.skip(!!viewport && viewport.width <= 768, "Hub mode controls require desktop viewport");

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
    await expect(page.getByTestId("network-graph")).toBeVisible({
      timeout: 30000,
    });
  });

  test("ShowMoreButton is visible on initial load", async ({ page }) => {
    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });
    await expect(btn).toContainText(/Showing \d+ of \d+/);
    await expect(btn).toContainText("Show more");
  });

  test("clicking ShowMoreButton expands node count", async ({ page }) => {
    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // Capture initial count text
    const initialText = await btn.textContent();

    // Click to expand (compact → medium)
    await btn.click();

    // After click: either text changes (dataset > 50) or button disappears (small dataset fully expanded)
    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await expect(btn).not.toHaveText(initialText!, { timeout: 3000 });
    } else {
      await expect(btn).not.toBeVisible({ timeout: 1000 });
    }
  });

  test("two clicks reveals all nodes and hides button", async ({ page }) => {
    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // First click: compact → medium
    await btn.click();

    // If button still visible after first click, click again to go to full
    const stillVisibleAfterFirst = await btn.isVisible().catch(() => false);
    if (stillVisibleAfterFirst) {
      await btn.click();
    }

    // After all clicks, button should not be visible (fully expanded)
    await expect(btn).not.toBeVisible({ timeout: 3000 });
  });

  test("Show Less button appears after expansion and reverses level", async ({ page }) => {
    const moreBtn = page.getByTestId("show-more-btn");
    const lessBtn = page.getByTestId("show-less-btn");
    await expect(moreBtn).toBeVisible({ timeout: 5000 });

    // Show less should not be visible at compact
    await expect(lessBtn).not.toBeVisible();

    // Expand to medium
    await moreBtn.click();
    await expect(lessBtn).toBeVisible({ timeout: 3000 });

    // Click show less to return to compact
    await lessBtn.click();

    // Should be back at compact — show less hidden, show more visible
    await expect(lessBtn).not.toBeVisible({ timeout: 3000 });
    await expect(moreBtn).toBeVisible();
  });

  test("graph renders without errors at each hub level", async ({ page }) => {
    // Verify no console errors during expansion
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));

    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // Expand through all levels
    await btn.click();

    // If button still visible after first click, click again to reach full
    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await btn.click();
      await expect(btn).not.toBeVisible({ timeout: 3000 });
    }

    // No JS errors during expansion
    expect(errors).toHaveLength(0);
  });

  test("search auto-reveal works with hub mode", async ({ page }) => {
    // Find the search input
    const searchInput = page.getByTestId("search-input");
    test.skip(!(await searchInput.isVisible()), "SearchInput component not rendered");

    const inputField = searchInput.locator("input");
    await inputField.fill("Charles");

    // Wait for dropdown
    const dropdown = searchInput.getByTestId("search-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Select first result
    const firstResult = dropdown.getByTestId("search-item").first();
    await expect(firstResult).toBeVisible();
    await firstResult.click();

    // Graph should center on the node (no toast error about "not in current view")
    // If the node was hidden, hub mode should have auto-expanded
    const toastVisible = await page
      .locator("text=Node not in current view")
      .isVisible()
      .catch(() => false);
    expect(toastVisible).toBe(false);
  });

  test("nodes display +N more badge labels at compact level", async ({ page }) => {
    await waitForLayoutSettled(page);

    const cy = await getCytoscapeInstance(page);
    const badgeNodes = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (cyInst: any) => {
        if (!cyInst) return [];
        return cyInst
          .nodes()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .filter((n: any) => {
            const label: string = n.data("label") || "";
            return label.includes("+");
          })
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .map((n: any) => ({
            id: n.id(),
            label: n.data("label") as string,
            hiddenCount: n.data("hiddenCount") as number,
          }));
      },
      cy,
    );

    // At compact level (25 nodes out of 200+), many nodes should have badges
    expect(badgeNodes.length).toBeGreaterThan(0);

    // Verify badge format: "Name  +N" where N > 0
    for (const node of badgeNodes) {
      expect(node.hiddenCount).toBeGreaterThan(0);
      expect(node.label).toMatch(/\+\d+/);
    }
  });

  test("expand all to full removes badge labels", async ({ page }) => {
    await waitForLayoutSettled(page);

    // Verify badges exist at compact level before expanding
    const cy = await getCytoscapeInstance(page);
    const hasBadgesInitially = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (cyInst: any) => {
        if (!cyInst) return false;
        return cyInst
          .nodes()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .some((n: any) => (n.data("hiddenCount") || 0) > 0);
      },
      cy,
    );

    test.skip(!hasBadgesInitially, "No badge nodes at compact level — dataset may be small");

    // Expand to full by clicking Show More (up to twice: compact → medium → full)
    const btn = page.getByTestId("show-more-btn");
    await btn.click();
    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await btn.click();
    }

    // Wait for layout to settle after full expansion
    await waitForLayoutSettled(page);

    // At full level, no nodes should have hidden counts
    const cyAfter = await getCytoscapeInstance(page);
    const badgeCountAfter = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (cyInst: any) => {
        if (!cyInst) return 0;
        return cyInst
          .nodes()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .filter((n: any) => (n.data("hiddenCount") || 0) > 0).length;
      },
      cyAfter,
    );

    expect(badgeCountAfter).toBe(0);
  });

  test("clicking a node with hidden neighbors expands its neighborhood", async ({ page }) => {
    await waitForLayoutSettled(page);

    // Find a node with hidden neighbors (skip for small datasets)
    const cy = await getCytoscapeInstance(page);
    const targetNode = await page.evaluate(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (cyInst: any) => {
        if (!cyInst) return null;
        const node = cyInst
          .nodes()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .filter((n: any) => (n.data("hiddenCount") || 0) > 0)
          .first();
        if (node.length === 0) return null;
        return { id: node.id() as string };
      },
      cy,
    );

    test.skip(!targetNode, "No nodes with hidden neighbors found at compact level");

    // Get initial node count
    const initialCount = await getNodeCount(page);

    // Emit a Cytoscape "tap" event directly on the node instead of using
    // coordinate-based mouse.click(), which suffers from sub-pixel offset
    // mismatches between Cytoscape's canvas coordinates and the DOM bounding box.
    // NOTE: This tests the data pipeline (hidden neighbors expand) but not the
    // full interaction path — the emitted event lacks position/mouse properties
    // that a real user tap would include.
    await tapNode(page, targetNode!.id);

    // Wait for the node count to increase (hidden neighbors added)
    // then for the layout animation to finish settling
    await waitForNodeCountAbove(page, initialCount);

    // Node count should have increased (hidden neighbors were added)
    const afterCount = await getNodeCount(page);

    expect(afterCount).toBeGreaterThan(initialCount);
  });
});
