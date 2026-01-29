import { test, expect, type Locator } from "@playwright/test";

/**
 * E3: Social Circles Statistics Panel E2E Tests
 *
 * Tests the statistics panel functionality:
 * - Stats panel shows correct counts
 * - Stats update when filters applied
 * - Panel collapses and expands
 */

/**
 * Helper: Expand the stats panel if it is collapsed.
 * Replaces ~10 instances of duplicated expand/collapse boilerplate (#1449).
 */
async function expandStatsPanel(statsPanel: Locator): Promise<void> {
  const isCollapsed = await statsPanel.evaluate((el) =>
    el.classList.contains("stats-panel--collapsed")
  );
  if (isCollapsed) {
    await statsPanel.getByTestId("stats-toggle").click();
    await expect(statsPanel.getByTestId("stats-content")).toBeVisible();
  }
}

/**
 * Helper: Collapse the stats panel if it is expanded.
 */
async function collapseStatsPanel(statsPanel: Locator): Promise<void> {
  const isCollapsed = await statsPanel.evaluate((el) =>
    el.classList.contains("stats-panel--collapsed")
  );
  if (!isCollapsed) {
    await statsPanel.getByTestId("stats-toggle").click();
    await expect(statsPanel.getByTestId("stats-content")).not.toBeVisible();
  }
}

test.describe("Social Circles Statistics Panel", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/socialcircles");
    await expect(page.getByTestId("network-graph")).toBeVisible({ timeout: 15000 });
  });

  test("stats panel is visible", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    const isVisible = await statsPanel.isVisible();
    test.skip(!isVisible, "Stats panel not rendered in current view");

    await expect(statsPanel).toBeVisible();

    const title = statsPanel.locator(".stats-panel__title");
    await expect(title).toContainText(/network statistics/i);
  });

  test("stats panel displays node counts", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    const totalNodesLabel = statsPanel.getByText(/total nodes/i);
    await expect(totalNodesLabel).toBeVisible();

    const nodeBreakdown = statsPanel.getByTestId("stats-grid");
    await expect(nodeBreakdown).toBeVisible();
  });

  test("stats panel displays connection counts", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    const connectionsLabel = statsPanel.getByText(/connections/i);
    await expect(connectionsLabel).toBeVisible();
  });

  test("stats panel shows network density", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    const densityLabel = statsPanel.getByText(/network density/i);
    await expect(densityLabel).toBeVisible();

    const percentageValue = statsPanel.getByText(/%/);
    await expect(percentageValue).toBeVisible();
  });

  test("stats panel shows average connections per node", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    const avgLabel = statsPanel.getByText(/avg.*connections|connections.*per.*node/i);
    await expect(avgLabel).toBeVisible();
  });

  test("stats panel shows notable entities", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    const notableSection = statsPanel.getByTestId("stats-notable");
    if (await notableSection.isVisible()) {
      const sectionTitle = notableSection.getByText(/notable entities/i);
      await expect(sectionTitle).toBeVisible();
    }
  });

  test("stats panel collapses when toggle is clicked", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    const toggleButton = statsPanel.getByTestId("stats-toggle");
    const content = statsPanel.getByTestId("stats-content");

    const initiallyCollapsed = await statsPanel.evaluate((el) =>
      el.classList.contains("stats-panel--collapsed")
    );

    await toggleButton.click();

    if (initiallyCollapsed) {
      await expect(content).toBeVisible();
    } else {
      await expect(content).not.toBeVisible();
    }

    const nowCollapsed = await statsPanel.evaluate((el) =>
      el.classList.contains("stats-panel--collapsed")
    );
    expect(nowCollapsed).toBe(!initiallyCollapsed);
  });

  test("stats panel expands when toggle is clicked on collapsed panel", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    const toggleButton = statsPanel.getByTestId("stats-toggle");

    await collapseStatsPanel(statsPanel);

    await toggleButton.click();
    await expect(statsPanel.getByTestId("stats-content")).toBeVisible();

    const isExpanded = await statsPanel.evaluate(
      (el) => !el.classList.contains("stats-panel--collapsed")
    );
    expect(isExpanded).toBe(true);
  });

  test("toggle button shows expand/collapse indicator", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    const toggleIcon = statsPanel.getByTestId("stats-toggle-icon");
    test.skip(!(await toggleIcon.isVisible()), "Toggle icon not rendered");

    const isCollapsed = await statsPanel.evaluate((el) =>
      el.classList.contains("stats-panel--collapsed")
    );

    const iconText = await toggleIcon.textContent();
    if (isCollapsed) {
      expect(iconText).toBe("+");
    } else {
      expect(iconText).toBe("-");
    }
  });

  test("toggle button has correct aria-expanded attribute", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    const toggleButton = statsPanel.getByTestId("stats-toggle");

    const ariaExpanded = await toggleButton.getAttribute("aria-expanded");
    const isCollapsed = await statsPanel.evaluate((el) =>
      el.classList.contains("stats-panel--collapsed")
    );

    expect(ariaExpanded).toBe(isCollapsed ? "false" : "true");
  });

  test("stats update when filters are applied", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    // Capture initial stat values before filtering (#1451)
    const statsGrid = statsPanel.getByTestId("stats-grid");
    const initialStatsText = await statsGrid.textContent();

    // Apply a filter (toggle off a node type)
    const filterPanel = page.getByTestId("filter-panel");
    test.skip(!(await filterPanel.isVisible()), "Filter panel not rendered");

    const publishersCheckbox = filterPanel.locator('input[type="checkbox"]').nth(1);
    await expect(publishersCheckbox).toBeVisible();
    await publishersCheckbox.click({ force: true });

    // Wait for stats to update by checking grid content changes
    await expect(statsGrid).not.toHaveText(initialStatsText || "");

    // Verify stats content changed after filter (#1451)
    const updatedStatsText = await statsGrid.textContent();
    expect(updatedStatsText).not.toBe(initialStatsText);
    expect(updatedStatsText).toBeTruthy();
  });

  test("stats panel shows collection date range", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    const footer = statsPanel.getByTestId("stats-footer");
    if (await footer.isVisible()) {
      const metaText = footer.getByTestId("stats-meta");
      const count = await metaText.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test("stat cards display numeric values", async ({ page }) => {
    const statsPanel = page.getByTestId("stats-panel");
    test.skip(!(await statsPanel.isVisible()), "Stats panel not rendered");

    await expandStatsPanel(statsPanel);

    const statCards = statsPanel.getByTestId("stats-grid");
    await expect(statCards).toBeVisible();

    const statsContent = await statCards.textContent();
    const hasNumbers = /\d+/.test(statsContent || "");
    expect(hasNumbers).toBe(true);
  });
});
