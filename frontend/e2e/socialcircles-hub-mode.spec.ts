import { test, expect } from "@playwright/test";

/**
 * Social Circles Hub Mode E2E Tests
 *
 * Tests progressive disclosure: initial compact view (25 nodes),
 * ShowMoreButton expansion, and full graph reveal.
 */

test.describe("Social Circles Hub Mode", () => {
  test.beforeEach(async ({ page }) => {
    const viewport = page.viewportSize();
    test.skip(
      !!viewport && viewport.width <= 768,
      "Hub mode controls require desktop viewport",
    );

    await page.goto("/social-circles");
    await expect(page.getByTestId("network-graph")).toBeVisible({
      timeout: 15000,
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

  test("Show Less button appears after expansion and reverses level", async ({
    page,
  }) => {
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
    test.skip(
      !(await searchInput.isVisible()),
      "SearchInput component not rendered",
    );

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

  test("nodes display +N more badge labels at compact level", async ({
    page,
  }) => {
    // Wait for graph to render and COSE layout to settle
    await page.waitForTimeout(2000);

    // Access Cytoscape instance via internal _cyreg on the container element
    const badgeNodes = await page.evaluate(() => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      if (!cy) return [];
      return cy
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
    });

    // At compact level (25 nodes out of 200+), many nodes should have badges
    expect(badgeNodes.length).toBeGreaterThan(0);

    // Verify badge format: "Name  +N" where N > 0
    for (const node of badgeNodes) {
      expect(node.hiddenCount).toBeGreaterThan(0);
      expect(node.label).toMatch(/\+\d+/);
    }
  });

  test("expand all to full removes badge labels", async ({ page }) => {
    // Wait for graph to render and layout to settle
    await page.waitForTimeout(2000);

    // Verify badges exist at compact level before expanding
    const hasBadgesInitially = await page.evaluate(() => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      if (!cy) return false;
      return cy
        .nodes()
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .some((n: any) => (n.data("hiddenCount") || 0) > 0);
    });

    test.skip(
      !hasBadgesInitially,
      "No badge nodes at compact level — dataset may be small",
    );

    // Expand to full by clicking Show More (up to twice: compact → medium → full)
    const btn = page.getByTestId("show-more-btn");
    await btn.click();
    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await btn.click();
    }

    // Wait for layout to settle after full expansion
    await page.waitForTimeout(2000);

    // At full level, no nodes should have hidden counts
    const badgeCountAfter = await page.evaluate(() => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      if (!cy) return 0;
      return cy
        .nodes()
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .filter((n: any) => (n.data("hiddenCount") || 0) > 0).length;
    });

    expect(badgeCountAfter).toBe(0);
  });

  test("clicking a node with hidden neighbors expands its neighborhood", async ({
    page,
  }) => {
    // Wait for graph to render and layout to settle
    await page.waitForTimeout(2000);

    // Find a node with hidden neighbors using Cytoscape API
    const targetNode = await page.evaluate(() => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      if (!cy) return null;
      const node = cy
        .nodes()
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .filter((n: any) => (n.data("hiddenCount") || 0) > 0)
        .first();
      if (node.length === 0) return null;
      const pos = node.renderedPosition();
      return {
        id: node.id() as string,
        hiddenCount: node.data("hiddenCount") as number,
        x: pos.x as number,
        y: pos.y as number,
      };
    });

    test.skip(
      !targetNode,
      "No nodes with hidden neighbors found at compact level",
    );

    // Get initial node count
    const initialCount = await page.evaluate(() => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      return cy ? (cy.nodes().length as number) : 0;
    });

    // Click the node at its rendered position within the graph viewport
    const graphEl = page.getByTestId("network-graph");
    const graphBox = await graphEl.boundingBox();
    if (graphBox && targetNode) {
      await page.mouse.click(
        graphBox.x + targetNode.x,
        graphBox.y + targetNode.y,
      );
    }

    // Wait for expansion animation and layout to settle
    await page.waitForTimeout(1500);

    // Node count should have increased (hidden neighbors were added)
    const afterCount = await page.evaluate(() => {
      const container = document.querySelector(
        "[data-testid='network-graph']",
      ) as HTMLElement | null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cy = (container as any)?._cyreg?.cy;
      return cy ? (cy.nodes().length as number) : 0;
    });

    expect(afterCount).toBeGreaterThan(initialCount);
  });
});
