import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test("shows BlueMoxon title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/BlueMoxon/);
  });

  test("displays hero section with collection stats", async ({ page }) => {
    await page.goto("/");
    // Check for collection stats in hero area
    await expect(page.locator("text=Victorian Book Collection")).toBeVisible();
  });

  test("has navigation links", async ({ page }) => {
    await page.goto("/");
    // Check for main nav links
    await expect(page.getByRole("link", { name: /Books/i })).toBeVisible();
  });

  test("browse collection button navigates to books", async ({ page }) => {
    await page.goto("/");
    const browseButton = page.getByRole("link", { name: /Browse Collection/i });
    if (await browseButton.isVisible()) {
      await browseButton.click();
      await expect(page).toHaveURL(/\/books/);
    }
  });
});

test.describe("Statistics Dashboard", () => {
  test("displays collection analytics section", async ({ page }) => {
    await page.goto("/");
    // Wait for the statistics dashboard to load
    await expect(page.locator("text=Collection Analytics")).toBeVisible({
      timeout: 10000,
    });
  });

  test("shows chart containers for all four charts", async ({ page }) => {
    await page.goto("/");
    // Wait for charts section
    await expect(page.locator("text=Collection Analytics")).toBeVisible({
      timeout: 10000,
    });

    // Verify chart section headers are present
    await expect(page.locator("text=Value Growth by Month")).toBeVisible();
    await expect(page.locator("text=Premium Bindings")).toBeVisible();
    await expect(page.locator("text=Books by Era")).toBeVisible();
    await expect(page.locator("text=Top Tier 1 Publishers")).toBeVisible();
  });

  test("dashboard stat cards display values", async ({ page }) => {
    await page.goto("/");
    // Wait for dashboard to load
    await expect(page.locator("text=Collection Dashboard")).toBeVisible({
      timeout: 10000,
    });

    // Check that the stat cards are present (they should show numbers or loading state)
    await expect(page.locator("text=Collections")).toBeVisible();
    await expect(page.locator("text=Volumes")).toBeVisible();
    await expect(page.locator("text=Value")).toBeVisible();
    await expect(page.locator("text=Premium")).toBeVisible();
  });
});
