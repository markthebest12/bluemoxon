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
