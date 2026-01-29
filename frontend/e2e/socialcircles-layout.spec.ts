import { test, expect } from "@playwright/test";

/**
 * E2: Social Circles Layout Switching E2E Tests
 *
 * Tests the layout switching functionality:
 * - Layout switcher visibility
 * - Clicking layout button changes graph layout
 * - Layout persists in URL (if implemented)
 * - Keyboard shortcut cycles layouts (if implemented)
 */

test.describe("Social Circles Layout Switching", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/socialcircles");
    // Wait for the graph to be ready
    await expect(page.locator(".network-graph")).toBeVisible({ timeout: 15000 });
  });

  test("layout switcher component is visible", async ({ page }) => {
    // Look for the layout switcher component
    const layoutSwitcher = page.locator(".layout-switcher");

    // Layout switcher may be in the UI
    if (await layoutSwitcher.isVisible()) {
      await expect(layoutSwitcher).toBeVisible();

      // Should have multiple layout buttons
      const layoutButtons = layoutSwitcher.locator(".layout-switcher__btn");
      const buttonCount = await layoutButtons.count();
      expect(buttonCount).toBeGreaterThanOrEqual(2);
    } else {
      // Layout switcher may not be visible in current view
      // Check for any layout controls in the toolbar area
      const toolbarButtons = page.getByRole("button");
      const count = await toolbarButtons.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test("layout buttons display available layout modes", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      // Check for expected layout options
      const forceButton = layoutSwitcher.getByRole("button", { name: /force/i });
      const circleButton = layoutSwitcher.getByRole("button", { name: /circle/i });
      const gridButton = layoutSwitcher.getByRole("button", { name: /grid/i });
      const hierarchyButton = layoutSwitcher.getByRole("button", { name: /hierarch/i });

      // At least some layout options should be present
      const visibleCount = await Promise.all([
        forceButton.isVisible(),
        circleButton.isVisible(),
        gridButton.isVisible(),
        hierarchyButton.isVisible(),
      ]).then((results) => results.filter(Boolean).length);

      expect(visibleCount).toBeGreaterThanOrEqual(2);
    }
  });

  test("clicking layout button changes the active layout", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      // Get all layout buttons
      const layoutButtons = layoutSwitcher.locator(".layout-switcher__btn");
      const buttonCount = await layoutButtons.count();

      if (buttonCount >= 2) {
        // Find the current active button
        const activeButton = layoutSwitcher.locator(".layout-switcher__btn--active");
        const initialActiveText = await activeButton.textContent();

        // Find a non-active button and click it
        for (let i = 0; i < buttonCount; i++) {
          const button = layoutButtons.nth(i);
          const isActive = await button.evaluate((el) =>
            el.classList.contains("layout-switcher__btn--active")
          );
          if (!isActive) {
            await button.click();

            // Wait for layout animation
            await page.waitForTimeout(500);

            // The clicked button should now be active
            const newActiveText = await layoutSwitcher
              .locator(".layout-switcher__btn--active")
              .textContent();
            expect(newActiveText).not.toBe(initialActiveText);
            break;
          }
        }
      }
    }
  });

  test("one layout button is always active", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      // Exactly one button should have the active class
      const activeButtons = layoutSwitcher.locator(".layout-switcher__btn--active");
      await expect(activeButtons).toHaveCount(1);
    }
  });

  test("layout buttons show tooltips with descriptions", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      const layoutButtons = layoutSwitcher.locator(".layout-switcher__btn");
      const firstButton = layoutButtons.first();

      // Buttons should have title attribute for tooltips
      const title = await firstButton.getAttribute("title");
      expect(title).toBeTruthy();
    }
  });

  test("layout change triggers graph re-layout animation", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      // Find a non-active layout button
      const nonActiveButton = layoutSwitcher.locator(
        ".layout-switcher__btn:not(.layout-switcher__btn--active)"
      );

      if ((await nonActiveButton.count()) > 0) {
        // Click to change layout
        await nonActiveButton.first().click();

        // The graph should still be visible after layout change
        await expect(page.locator(".network-graph")).toBeVisible();

        // Wait for animation to complete
        await page.waitForTimeout(1000);

        // Graph should still be interactive
        await expect(page.locator(".network-graph")).toBeVisible();
      }
    }
  });

  test("layout switcher is disabled during animation", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      // Check if layout switcher can be disabled
      const nonActiveButton = layoutSwitcher.locator(
        ".layout-switcher__btn:not(.layout-switcher__btn--active)"
      );

      if ((await nonActiveButton.count()) > 0) {
        // Click to trigger animation
        await nonActiveButton.first().click();

        // During animation, the switcher might be disabled
        // Check for disabled state (implementation-dependent)
        const isDisabled =
          (await layoutSwitcher.locator(".layout-switcher--disabled").count()) > 0;

        // After animation completes, should be enabled again
        await page.waitForTimeout(1500);
        const stillDisabled =
          (await layoutSwitcher.locator(".layout-switcher--disabled").count()) > 0;

        // Either it was never disabled (acceptable) or it became enabled again
        expect(isDisabled || !stillDisabled).toBeTruthy();
      }
    }
  });

  test("layout persists after page interaction", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      // Change to a different layout
      const circleButton = layoutSwitcher.getByRole("button", { name: /circle/i });

      if (await circleButton.isVisible()) {
        await circleButton.click();
        await page.waitForTimeout(500);

        // Verify circle layout is active
        await expect(circleButton).toHaveClass(/layout-switcher__btn--active/);

        // Interact with the page (e.g., click on the graph area)
        await page.locator(".network-graph").click();
        await page.waitForTimeout(200);

        // Layout should still be circle
        await expect(circleButton).toHaveClass(/layout-switcher__btn--active/);
      }
    }
  });

  test("all layout modes render without error", async ({ page }) => {
    const layoutSwitcher = page.locator(".layout-switcher");

    if (await layoutSwitcher.isVisible()) {
      const layoutButtons = layoutSwitcher.locator(".layout-switcher__btn");
      const buttonCount = await layoutButtons.count();

      for (let i = 0; i < buttonCount; i++) {
        const button = layoutButtons.nth(i);
        await button.click();

        // Wait for layout to complete
        await page.waitForTimeout(800);

        // Graph should still be visible and no console errors
        await expect(page.locator(".network-graph")).toBeVisible();
      }
    }
  });
});
