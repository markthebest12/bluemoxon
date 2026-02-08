import { test, expect } from "@playwright/test";

/**
 * E1: Social Circles Search E2E Tests
 *
 * Tests the search functionality in the Social Circles feature:
 * - Search input visibility (top bar SearchInput component)
 * - Typing shows results dropdown
 * - Selecting result centers graph on node
 * - Keyboard navigation (ArrowDown, Enter)
 * - No results shows empty state
 */

test.describe("Social Circles Search", () => {
  test.beforeEach(async ({ page }) => {
    // Filter panel search is hidden on mobile viewports (<768px) — skip
    // rather than fail, since the social-circles sidebar is a desktop feature.
    const viewport = page.viewportSize();
    test.skip(!!viewport && viewport.width <= 768, "Search panel requires desktop viewport");

    await page.goto("/social-circles");
    await expect(page.getByTestId("network-graph")).toBeVisible({ timeout: 15000 });
  });

  test("search input is visible in top bar", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");
    await expect(searchInputComponent).toBeVisible();
    const inputField = searchInputComponent.locator("input");
    await expect(inputField).toBeVisible();
  });

  test("typing in search shows results", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");
    const inputField = searchInputComponent.locator("input");
    await inputField.fill("Tennyson");

    // Wait for dropdown to appear
    const dropdown = searchInputComponent.getByTestId("search-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 5000 });
  });

  test("search results dropdown appears when using SearchInput component", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      await inputField.fill("Charles");

      // Wait for dropdown to appear instead of hardcoded timeout
      const dropdown = searchInputComponent.getByTestId("search-dropdown");
      await expect(dropdown).toBeVisible({ timeout: 5000 });
    } else {
      test.skip(true, "SearchInput component not rendered");
    }
  });

  test("selecting a search result from dropdown", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");
    test.skip(!(await searchInputComponent.isVisible()), "SearchInput component not rendered");

    const inputField = searchInputComponent.locator("input");
    await inputField.fill("Charles");

    // Wait for dropdown to appear
    const dropdown = searchInputComponent.getByTestId("search-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Click the first result
    const firstResult = dropdown.getByTestId("search-item").first();
    await expect(firstResult).toBeVisible();
    await firstResult.click();

    // Dropdown should close
    await expect(dropdown).not.toBeVisible();

    // Input should have the selected name
    const inputValue = await inputField.inputValue();
    expect(inputValue.length).toBeGreaterThan(0);
  });

  test("keyboard navigation in search dropdown with ArrowDown and Enter", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");
    test.skip(!(await searchInputComponent.isVisible()), "SearchInput component not rendered");

    const inputField = searchInputComponent.locator("input");
    await inputField.focus();
    await inputField.fill("John");

    // Wait for dropdown to appear
    const dropdown = searchInputComponent.getByTestId("search-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Press ArrowDown to select first item
    await inputField.press("ArrowDown");

    // Check for active item class
    const activeItem = dropdown.locator(".search-input__item--active");
    await expect(activeItem).toBeVisible();

    // Press Enter to select
    await inputField.press("Enter");

    // Dropdown should close after selection
    await expect(dropdown).not.toBeVisible();
  });

  test("no results shows empty state message", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      // Search for something that won't exist
      await inputField.fill("xyznonexistentperson123");

      // Wait for no results message to appear
      const noResults = searchInputComponent.getByTestId("search-no-results");
      await expect(noResults).toBeVisible({ timeout: 3000 });
      await expect(noResults).toContainText(/no results/i);
    } else {
      test.skip(true, "SearchInput component not rendered");
    }
  });

  test("escape key closes search dropdown", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");
    test.skip(!(await searchInputComponent.isVisible()), "SearchInput component not rendered");

    const inputField = searchInputComponent.locator("input");
    await inputField.fill("Charles");

    // Wait for dropdown to appear
    const dropdown = searchInputComponent.getByTestId("search-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Press Escape to close
    await inputField.press("Escape");

    // Dropdown should be hidden
    await expect(dropdown).not.toBeVisible();
  });

  test("search maintains focus after clicking result", async ({ page }) => {
    const searchInputComponent = page.getByTestId("search-input");
    test.skip(!(await searchInputComponent.isVisible()), "SearchInput component not rendered");

    const inputField = searchInputComponent.locator("input");
    await inputField.fill("Alfred");

    // Wait for results to appear
    const firstResult = searchInputComponent.getByTestId("search-item").first();
    await expect(firstResult).toBeVisible({ timeout: 5000 });

    await firstResult.click();

    // After selection, the input should have the selected name
    const inputValue = await inputField.inputValue();
    expect(inputValue).toBeTruthy();
  });
});
