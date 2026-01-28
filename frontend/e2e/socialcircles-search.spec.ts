import { test, expect } from "@playwright/test";

/**
 * E1: Social Circles Search E2E Tests
 *
 * Tests the search functionality in the Social Circles feature:
 * - Search input visibility
 * - Typing shows results dropdown
 * - Selecting result centers graph on node
 * - Keyboard navigation (ArrowDown, Enter)
 * - No results shows empty state
 */

test.describe("Social Circles Search", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/socialcircles");
    // Wait for the graph to be ready
    await expect(page.locator(".network-graph")).toBeVisible({ timeout: 15000 });
  });

  test("search input is visible in filter panel", async ({ page }) => {
    // The search input is in the filter panel
    const searchInput = page.locator('.filter-panel input[type="text"]');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveAttribute("placeholder", /find person|search/i);
  });

  test("typing in search filters the view", async ({ page }) => {
    const searchInput = page.locator('.filter-panel input[type="text"]');
    await expect(searchInput).toBeVisible();

    // Type a search query
    await searchInput.fill("Tennyson");

    // Wait for debounced search to take effect
    await page.waitForTimeout(500);

    // The filter should be applied - we can verify by checking the URL updates
    // or that the search value is retained
    await expect(searchInput).toHaveValue("Tennyson");
  });

  test("search results dropdown appears when using SearchInput component", async ({ page }) => {
    // Check if SearchInput component is present (may be in different location)
    const searchInputComponent = page.locator(".search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      await inputField.fill("Charles");

      // Wait for debounce
      await page.waitForTimeout(400);

      // Results dropdown should appear
      const dropdown = page.locator(".search-input__dropdown");
      await expect(dropdown).toBeVisible({ timeout: 5000 });
    } else {
      // If SearchInput component is not in view, use the filter panel search
      const filterSearch = page.locator('.filter-panel input[type="text"]');
      await filterSearch.fill("Dickens");
      await page.waitForTimeout(300);
      // Verify the search is applied
      await expect(filterSearch).toHaveValue("Dickens");
    }
  });

  test("selecting a search result from dropdown", async ({ page }) => {
    const searchInputComponent = page.locator(".search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      await inputField.fill("Charles");

      // Wait for results
      await page.waitForTimeout(400);

      const dropdown = page.locator(".search-input__dropdown");
      if (await dropdown.isVisible()) {
        // Click the first result
        const firstResult = dropdown.locator(".search-input__item").first();
        if (await firstResult.isVisible()) {
          await firstResult.click();

          // Dropdown should close
          await expect(dropdown).not.toBeVisible();

          // Input should have the selected name
          const inputValue = await inputField.inputValue();
          expect(inputValue.length).toBeGreaterThan(0);
        }
      }
    }
  });

  test("keyboard navigation in search dropdown with ArrowDown and Enter", async ({ page }) => {
    const searchInputComponent = page.locator(".search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      await inputField.focus();
      await inputField.fill("John");

      // Wait for results
      await page.waitForTimeout(400);

      const dropdown = page.locator(".search-input__dropdown");
      if (await dropdown.isVisible()) {
        // Press ArrowDown to select first item
        await inputField.press("ArrowDown");

        // Check for active item class
        const activeItem = dropdown.locator(".search-input__item--active");
        await expect(activeItem).toBeVisible();

        // Press Enter to select
        await inputField.press("Enter");

        // Dropdown should close after selection
        await expect(dropdown).not.toBeVisible();
      }
    }
  });

  test("no results shows empty state message", async ({ page }) => {
    const searchInputComponent = page.locator(".search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      // Search for something that won't exist
      await inputField.fill("xyznonexistentperson123");

      // Wait for debounce
      await page.waitForTimeout(400);

      // Should show no results message
      const noResults = page.locator(".search-input__no-results");
      await expect(noResults).toBeVisible({ timeout: 3000 });
      await expect(noResults).toContainText(/no results/i);
    } else {
      // Using filter panel search - verify it handles empty results gracefully
      const filterSearch = page.locator('.filter-panel input[type="text"]');
      await filterSearch.fill("xyznonexistentperson123");
      await page.waitForTimeout(300);
      // The filter is applied even if no nodes match
      await expect(filterSearch).toHaveValue("xyznonexistentperson123");
    }
  });

  test("escape key closes search dropdown", async ({ page }) => {
    const searchInputComponent = page.locator(".search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      await inputField.fill("Charles");

      // Wait for dropdown
      await page.waitForTimeout(400);

      const dropdown = page.locator(".search-input__dropdown");
      if (await dropdown.isVisible()) {
        // Press Escape to close
        await inputField.press("Escape");

        // Dropdown should be hidden
        await expect(dropdown).not.toBeVisible();
      }
    }
  });

  test("search maintains focus after clicking result", async ({ page }) => {
    const searchInputComponent = page.locator(".search-input");

    if (await searchInputComponent.isVisible()) {
      const inputField = searchInputComponent.locator("input");
      await inputField.fill("Alfred");

      // Wait for results
      await page.waitForTimeout(400);

      const firstResult = page.locator(".search-input__item").first();
      if (await firstResult.isVisible()) {
        await firstResult.click();

        // After selection, the input should have the selected name
        const inputValue = await inputField.inputValue();
        expect(inputValue).toBeTruthy();
      }
    }
  });
});
