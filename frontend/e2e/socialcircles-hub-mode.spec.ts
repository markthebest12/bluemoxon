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

    // Button should still be visible with updated count (medium level)
    // or may have disappeared if total nodes < 50
    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      const updatedText = await btn.textContent();
      // Count should have increased
      expect(updatedText).not.toBe(initialText);
    }
  });

  test("two clicks reveals all nodes and hides button", async ({ page }) => {
    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // Click twice: compact → medium → full
    await btn.click();
    // Small delay for reactivity
    await page.waitForTimeout(300);

    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await btn.click();
      // After full expansion, button should disappear
      await expect(btn).not.toBeVisible({ timeout: 3000 });
    }
  });

  test("graph renders without errors at each hub level", async ({ page }) => {
    // Verify no console errors during expansion
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));

    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // Expand through levels
    await btn.click();
    await page.waitForTimeout(500);

    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await btn.click();
      await page.waitForTimeout(500);
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
});
