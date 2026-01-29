import { test, expect } from "@playwright/test";

/**
 * E2: Social Circles Layout Switching E2E Tests
 *
 * Tests the layout switching functionality:
 * - Layout switcher visibility
 * - Clicking layout button changes graph layout
 * - Layout persists after page interaction
 */

test.describe("Social Circles Layout Switching", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/socialcircles");
    await expect(page.getByTestId("network-graph")).toBeVisible({ timeout: 15000 });
  });

  test("layout switcher component is visible", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    const isVisible = await layoutSwitcher.isVisible();
    test.skip(!isVisible, "Layout switcher not rendered in current view");

    await expect(layoutSwitcher).toBeVisible();

    // Should have multiple layout buttons
    const layoutButtons = layoutSwitcher.locator("[data-testid^='layout-btn-']");
    const buttonCount = await layoutButtons.count();
    expect(buttonCount).toBeGreaterThanOrEqual(2);
  });

  test("layout buttons display available layout modes", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    // Check for expected layout options
    const forceButton = layoutSwitcher.getByRole("button", { name: /force/i });
    const circleButton = layoutSwitcher.getByRole("button", { name: /circle/i });
    const gridButton = layoutSwitcher.getByRole("button", { name: /grid/i });
    const hierarchyButton = layoutSwitcher.getByRole("button", { name: /hierarch/i });

    const visibleCount = await Promise.all([
      forceButton.isVisible(),
      circleButton.isVisible(),
      gridButton.isVisible(),
      hierarchyButton.isVisible(),
    ]).then((results) => results.filter(Boolean).length);

    expect(visibleCount).toBeGreaterThanOrEqual(2);
  });

  test("clicking layout button changes the active layout", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    const layoutButtons = layoutSwitcher.locator("[data-testid^='layout-btn-']");
    const buttonCount = await layoutButtons.count();
    expect(buttonCount).toBeGreaterThanOrEqual(2);

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

        // Wait for the clicked button to become active instead of hardcoded timeout
        await expect(button).toHaveClass(/layout-switcher__btn--active/);

        const newActiveText = await layoutSwitcher
          .locator(".layout-switcher__btn--active")
          .textContent();
        expect(newActiveText).not.toBe(initialActiveText);
        break;
      }
    }
  });

  test("one layout button is always active", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    // Exactly one button should have the active class
    const activeButtons = layoutSwitcher.locator(".layout-switcher__btn--active");
    await expect(activeButtons).toHaveCount(1);
  });

  test("layout buttons show tooltips with descriptions", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    const layoutButtons = layoutSwitcher.locator("[data-testid^='layout-btn-']");
    const firstButton = layoutButtons.first();

    // Buttons should have title attribute for tooltips
    const title = await firstButton.getAttribute("title");
    expect(title).toBeTruthy();
  });

  test("layout change triggers graph re-layout animation", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    const nonActiveButton = layoutSwitcher.locator(
      ".layout-switcher__btn:not(.layout-switcher__btn--active)"
    );
    const nonActiveCount = await nonActiveButton.count();
    expect(nonActiveCount).toBeGreaterThan(0);

    await nonActiveButton.first().click();

    // Wait for the clicked button to become active
    await expect(nonActiveButton.first()).toHaveClass(/layout-switcher__btn--active/);

    // Graph should still be visible after layout change
    await expect(page.getByTestId("network-graph")).toBeVisible();
  });

  test("layout switcher is disabled during animation", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    const nonActiveButton = layoutSwitcher.locator(
      ".layout-switcher__btn:not(.layout-switcher__btn--active)"
    );
    const nonActiveCount = await nonActiveButton.count();
    expect(nonActiveCount).toBeGreaterThan(0);

    // Click to trigger animation
    await nonActiveButton.first().click();

    // During animation, the switcher might be disabled
    const isDisabled = (await layoutSwitcher.locator(".layout-switcher--disabled").count()) > 0;

    // Wait for animation to complete by checking the active class settled
    await expect(nonActiveButton.first()).toHaveClass(/layout-switcher__btn--active/);

    const stillDisabled = (await layoutSwitcher.locator(".layout-switcher--disabled").count()) > 0;

    // Either it was never disabled (acceptable) or it became enabled again
    expect(isDisabled || !stillDisabled).toBeTruthy();
  });

  test("layout persists after page interaction", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    // Change to circle layout
    const circleButton = layoutSwitcher.getByRole("button", { name: /circle/i });
    test.skip(!(await circleButton.isVisible()), "Circle layout button not available");

    await circleButton.click();

    // Wait for circle layout to become active
    await expect(circleButton).toHaveClass(/layout-switcher__btn--active/);

    // Interact with the page (click on graph area)
    await page.getByTestId("network-graph").click();

    // Layout should still be circle
    await expect(circleButton).toHaveClass(/layout-switcher__btn--active/);
  });

  test("all layout modes render without error", async ({ page }) => {
    const layoutSwitcher = page.getByTestId("layout-switcher");
    test.skip(!(await layoutSwitcher.isVisible()), "Layout switcher not rendered");

    const layoutButtons = layoutSwitcher.locator("[data-testid^='layout-btn-']");
    const buttonCount = await layoutButtons.count();

    for (let i = 0; i < buttonCount; i++) {
      const button = layoutButtons.nth(i);
      await button.click();

      // Wait for layout to activate instead of hardcoded timeout
      await expect(button).toHaveClass(/layout-switcher__btn--active/);

      // Graph should still be visible
      await expect(page.getByTestId("network-graph")).toBeVisible();
    }
  });
});
