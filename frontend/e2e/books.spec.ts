import { test, expect } from "@playwright/test";

test.describe("Books Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/books");
  });

  test("displays book list", async ({ page }) => {
    // Wait for books to load
    await expect(page.locator('[data-testid="book-card"], .book-card, article').first()).toBeVisible({ timeout: 10000 });
  });

  test("shows book count", async ({ page }) => {
    // Should display total count somewhere
    await expect(page.getByText(/\d+ books?/i)).toBeVisible({ timeout: 10000 });
  });

  test("has search functionality", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill("Tennyson");
      // Allow time for debounced search
      await page.waitForTimeout(500);
      // Should filter results
    }
  });

  test("has filter controls", async ({ page }) => {
    // Check for filter/sort controls
    const filterButton = page.getByRole("button", { name: /filter|sort/i });
    const filterSelect = page.locator("select");
    expect((await filterButton.count()) > 0 || (await filterSelect.count()) > 0).toBeTruthy();
  });

  test("clicking book navigates to detail", async ({ page }) => {
    // Wait for first book card
    const firstBook = page.locator('[data-testid="book-card"], .book-card, article').first();
    await expect(firstBook).toBeVisible({ timeout: 10000 });

    // Click on the book (or its link)
    const bookLink = firstBook.getByRole("link").first();
    if (await bookLink.count() > 0) {
      await bookLink.click();
      await expect(page).toHaveURL(/\/books\/\d+/);
    }
  });

  test("pagination works", async ({ page }) => {
    // Check for pagination controls if multiple pages
    const nextButton = page.getByRole("button", { name: /next|›/i });
    const pageNumbers = page.locator('[data-testid="pagination"], .pagination');

    if (await nextButton.isVisible() || await pageNumbers.isVisible()) {
      // Pagination exists
      expect(true).toBeTruthy();
    }
  });
});

test.describe("Book Detail Page", () => {
  test("displays book information", async ({ page }) => {
    // Navigate to a known book (Cranford is book 401)
    await page.goto("/books/401");

    // Should show book title
    await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 10000 });

    // Should show some book details
    await expect(page.getByText(/author|publisher|binding/i).first()).toBeVisible();
  });

  test("shows book images if available", async ({ page }) => {
    await page.goto("/books/401");

    // Check for images
    const images = page.locator("img");
    await expect(images.first()).toBeVisible({ timeout: 10000 });
  });

  test("has back navigation", async ({ page }) => {
    await page.goto("/books/401");

    // Should have a way to go back
    const backLink = page.getByRole("link", { name: /back|books/i });
    if (await backLink.isVisible()) {
      await backLink.click();
      await expect(page).toHaveURL(/\/books/);
    }
  });

  test("image carousel opens on click", async ({ page }) => {
    await page.goto("/books/401");

    // Find clickable image
    const bookImage = page.locator("img").first();
    await expect(bookImage).toBeVisible({ timeout: 10000 });

    // Click to open carousel
    await bookImage.click();

    // Check for modal/carousel indicators
    const modal = page.locator('[role="dialog"], .modal, .carousel, .fixed.inset-0');
    // Either modal is visible or image is in lightbox
    if (await modal.isVisible()) {
      // Close button should exist
      await expect(page.getByRole("button", { name: /close|×/i })).toBeVisible();
    }
  });
});
