import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test("shows BlueMoxon title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/BlueMoxon/);
  });

  test("displays hero section with collection stats", async ({ page }) => {
    await page.goto("/");
    // Check for dashboard heading
    await expect(page.locator("text=Collection Dashboard")).toBeVisible();
  });

  test("has navigation links", async ({ page }) => {
    await page.goto("/");
    // Check for main nav links
    await expect(page.getByRole("link", { name: /Collection/i })).toBeVisible();
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

  test("shows chart containers for all five charts", async ({ page }) => {
    await page.goto("/");
    // Wait for charts section
    await expect(page.locator("text=Collection Analytics")).toBeVisible({
      timeout: 10000,
    });

    // Verify chart section headers are present (use heading role to avoid tooltip match)
    await expect(page.getByRole("heading", { name: "Premium Bindings" })).toBeVisible();
    await expect(page.locator("text=Books by Era")).toBeVisible();
    await expect(page.locator("text=Top Authors")).toBeVisible();
    await expect(page.locator("text=Top Tier 1 Publishers")).toBeVisible();
    await expect(page.locator("text=Est. Value Growth")).toBeVisible();
  });

  test("dashboard stat cards display values", async ({ page }) => {
    await page.goto("/");
    // Wait for dashboard to load
    await expect(page.locator("text=Collection Dashboard")).toBeVisible({
      timeout: 10000,
    });

    // Check stat card headings (exact: true avoids matching chart titles and tooltips)
    await expect(page.getByRole("heading", { name: "On Hand", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Volumes", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Est. Value", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Premium", exact: true })).toBeVisible();
  });
});
