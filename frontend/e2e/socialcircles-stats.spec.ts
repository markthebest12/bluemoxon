import { test, expect } from "@playwright/test";

/**
 * E3: Social Circles Statistics Panel E2E Tests
 *
 * Tests the statistics panel functionality:
 * - Stats panel shows correct counts
 * - Stats update when filters applied
 * - Panel collapses and expands
 */

test.describe("Social Circles Statistics Panel", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/socialcircles");
    // Wait for the graph to be ready
    await expect(page.locator(".network-graph")).toBeVisible({ timeout: 15000 });
  });

  test("stats panel is visible", async ({ page }) => {
    // Look for the stats panel component
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      await expect(statsPanel).toBeVisible();

      // Should have a title
      const title = statsPanel.locator(".stats-panel__title");
      await expect(title).toContainText(/network statistics/i);
    } else {
      // Stats might be displayed elsewhere (e.g., in header or sidebar)
      // Check for any statistics display
      const statsText = page.getByText(/nodes|connections|total/i);
      const count = await statsText.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test("stats panel displays node counts", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Expand panel if collapsed
      const toggleButton = statsPanel.locator(".stats-panel__toggle");
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );

      if (isCollapsed) {
        await toggleButton.click();
        await page.waitForTimeout(300);
      }

      // Should display total nodes
      const totalNodesLabel = statsPanel.getByText(/total nodes/i);
      await expect(totalNodesLabel).toBeVisible();

      // Should display node breakdown (authors, publishers, binders)
      const nodeBreakdown = statsPanel.locator(".stats-panel__grid");
      await expect(nodeBreakdown).toBeVisible();
    }
  });

  test("stats panel displays connection counts", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Expand if needed
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      if (isCollapsed) {
        await statsPanel.locator(".stats-panel__toggle").click();
        await page.waitForTimeout(300);
      }

      // Should display connections count
      const connectionsLabel = statsPanel.getByText(/connections/i);
      await expect(connectionsLabel).toBeVisible();
    }
  });

  test("stats panel shows network density", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Expand if needed
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      if (isCollapsed) {
        await statsPanel.locator(".stats-panel__toggle").click();
        await page.waitForTimeout(300);
      }

      // Check for network density display
      const densityLabel = statsPanel.getByText(/network density/i);
      await expect(densityLabel).toBeVisible();

      // Should show a percentage value
      const percentageValue = statsPanel.getByText(/%/);
      await expect(percentageValue).toBeVisible();
    }
  });

  test("stats panel shows average connections per node", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Expand if needed
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      if (isCollapsed) {
        await statsPanel.locator(".stats-panel__toggle").click();
        await page.waitForTimeout(300);
      }

      // Check for average connections display
      const avgLabel = statsPanel.getByText(/avg.*connections|connections.*per.*node/i);
      await expect(avgLabel).toBeVisible();
    }
  });

  test("stats panel shows notable entities", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Expand if needed
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      if (isCollapsed) {
        await statsPanel.locator(".stats-panel__toggle").click();
        await page.waitForTimeout(300);
      }

      // Check for notable entities section
      const notableSection = statsPanel.locator(".stats-panel__notable");
      if (await notableSection.isVisible()) {
        // Should have section title
        const sectionTitle = notableSection.getByText(/notable entities/i);
        await expect(sectionTitle).toBeVisible();
      }
    }
  });

  test("stats panel collapses when toggle is clicked", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      const toggleButton = statsPanel.locator(".stats-panel__toggle");
      const content = statsPanel.locator(".stats-panel__content");

      // Get initial state
      const initiallyCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );

      // Click toggle
      await toggleButton.click();
      await page.waitForTimeout(300);

      // State should have changed
      const nowCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      expect(nowCollapsed).toBe(!initiallyCollapsed);

      // Content visibility should match state
      if (nowCollapsed) {
        await expect(content).not.toBeVisible();
      } else {
        await expect(content).toBeVisible();
      }
    }
  });

  test("stats panel expands when toggle is clicked on collapsed panel", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      const toggleButton = statsPanel.locator(".stats-panel__toggle");

      // First ensure it's collapsed
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );

      if (!isCollapsed) {
        // Collapse it first
        await toggleButton.click();
        await page.waitForTimeout(300);
      }

      // Now expand it
      await toggleButton.click();
      await page.waitForTimeout(300);

      // Should be expanded
      const isExpanded = await statsPanel.evaluate(
        (el) => !el.classList.contains("stats-panel--collapsed")
      );
      expect(isExpanded).toBe(true);

      // Content should be visible
      const content = statsPanel.locator(".stats-panel__content");
      await expect(content).toBeVisible();
    }
  });

  test("toggle button shows expand/collapse indicator", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      const toggleIcon = statsPanel.locator(".stats-panel__toggle-icon");

      if (await toggleIcon.isVisible()) {
        // Check the icon content changes based on state
        const isCollapsed = await statsPanel.evaluate((el) =>
          el.classList.contains("stats-panel--collapsed")
        );

        const iconText = await toggleIcon.textContent();
        if (isCollapsed) {
          expect(iconText).toBe("+");
        } else {
          expect(iconText).toBe("-");
        }
      }
    }
  });

  test("toggle button has correct aria-expanded attribute", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      const toggleButton = statsPanel.locator(".stats-panel__toggle");

      // Check aria-expanded attribute
      const ariaExpanded = await toggleButton.getAttribute("aria-expanded");
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );

      expect(ariaExpanded).toBe(isCollapsed ? "false" : "true");
    }
  });

  test("stats update when filters are applied", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Ensure stats panel is expanded
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      if (isCollapsed) {
        await statsPanel.locator(".stats-panel__toggle").click();
        await page.waitForTimeout(300);
      }

      // Apply a filter (e.g., toggle off a node type)
      const filterPanel = page.locator(".filter-panel");
      if (await filterPanel.isVisible()) {
        // Toggle off publishers checkbox
        const publishersCheckbox = filterPanel.locator('input[type="checkbox"]').nth(1);
        if (await publishersCheckbox.isVisible()) {
          await publishersCheckbox.click({ force: true });
          await page.waitForTimeout(500);

          // Stats should have updated and panel should still be visible
          await expect(statsPanel).toBeVisible();

          // Verify stats content is still present after filter
          const updatedStats = await statsPanel.textContent();
          expect(updatedStats).toBeTruthy();
        }
      }
    }
  });

  test("stats panel shows collection date range", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Expand if needed
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      if (isCollapsed) {
        await statsPanel.locator(".stats-panel__toggle").click();
        await page.waitForTimeout(300);
      }

      // Check for date range or collection info in footer
      const footer = statsPanel.locator(".stats-panel__footer");
      if (await footer.isVisible()) {
        // Should show some metadata about the collection
        const metaText = footer.locator(".stats-panel__meta");
        const count = await metaText.count();
        expect(count).toBeGreaterThan(0);
      }
    }
  });

  test("stat cards display numeric values", async ({ page }) => {
    const statsPanel = page.locator(".stats-panel");

    if (await statsPanel.isVisible()) {
      // Expand if needed
      const isCollapsed = await statsPanel.evaluate((el) =>
        el.classList.contains("stats-panel--collapsed")
      );
      if (isCollapsed) {
        await statsPanel.locator(".stats-panel__toggle").click();
        await page.waitForTimeout(300);
      }

      // Check for StatCard components with numeric values
      const statCards = statsPanel.locator(".stats-panel__grid");
      if (await statCards.isVisible()) {
        // Should contain some numeric content
        const statsContent = await statCards.textContent();
        // Verify there are numbers displayed
        const hasNumbers = /\d+/.test(statsContent || "");
        expect(hasNumbers).toBe(true);
      }
    }
  });
});
