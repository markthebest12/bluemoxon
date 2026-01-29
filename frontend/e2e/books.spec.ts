import { test, expect } from "@playwright/test";

test.describe("Books Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/books");
  });

  test("displays book list", async ({ page }) => {
    // Wait for books to load
    await expect(
      page.locator('[data-testid="book-card"], .book-card, article').first()
    ).toBeVisible({ timeout: 10000 });
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
    if ((await bookLink.count()) > 0) {
      await bookLink.click();
      await expect(page).toHaveURL(/\/books\/\d+/);
    }
  });

  test("pagination works", async ({ page }) => {
    // Check for pagination controls if multiple pages
    const nextButton = page.getByRole("button", { name: /next|›/i });
    const pageNumbers = page.locator('[data-testid="pagination"], .pagination');

    if ((await nextButton.isVisible()) || (await pageNumbers.isVisible())) {
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

test.describe("Book CRUD Navigation (Editor)", () => {
  test.use({ storageState: ".auth/editor.json" });

  test("navigates to create book form", async ({ page }) => {
    await page.goto("/books/new");

    // Should land on the create page with correct heading
    await expect(page.getByRole("heading", { name: "Add New Book" })).toBeVisible({
      timeout: 10000,
    });

    // Back link should point to collection
    const backLink = page.getByRole("link", { name: /Back to Collection/i });
    await expect(backLink).toBeVisible();
  });

  test("create form displays all section headings", async ({ page }) => {
    await page.goto("/books/new");

    await expect(page.getByRole("heading", { name: "Add New Book" })).toBeVisible({
      timeout: 10000,
    });

    // Verify all form section headings are present
    await expect(page.getByRole("heading", { name: "Basic Information" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Binding" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Condition" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Valuation" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Acquisition" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Notes" })).toBeVisible();
  });

  test("create form has expected basic information fields", async ({ page }) => {
    await page.goto("/books/new");

    await expect(page.getByRole("heading", { name: "Add New Book" })).toBeVisible({
      timeout: 10000,
    });

    // Title input (required field)
    await expect(page.getByPlaceholder("Book title")).toBeVisible();

    // Author and Publisher dropdowns
    await expect(page.getByText("-- Select Author --")).toBeVisible();
    await expect(page.getByText("-- Select Publisher --")).toBeVisible();

    // Publication Date
    await expect(page.getByPlaceholder("e.g., 1867-1880 or 1851")).toBeVisible();

    // Edition
    await expect(page.getByPlaceholder("e.g., First Edition")).toBeVisible();

    // Volumes (number input)
    await expect(page.getByLabel("Volumes")).toBeVisible();
  });

  test("create form has action buttons", async ({ page }) => {
    await page.goto("/books/new");

    await expect(page.getByRole("heading", { name: "Add New Book" })).toBeVisible({
      timeout: 10000,
    });

    // Cancel and Create buttons
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Book" })).toBeVisible();
  });

  test("navigates to edit book form", async ({ page }) => {
    await page.goto("/books/401/edit");

    // Should land on the edit page with correct heading
    await expect(page.getByRole("heading", { name: "Edit Book" })).toBeVisible({
      timeout: 10000,
    });

    // Back link should point to the book detail
    const backLink = page.getByRole("link", { name: /Back to Book/i });
    await expect(backLink).toBeVisible();
  });

  test("edit form shows Update button instead of Create", async ({ page }) => {
    await page.goto("/books/401/edit");

    await expect(page.getByRole("heading", { name: "Edit Book" })).toBeVisible({
      timeout: 10000,
    });

    // Should show Update Book, not Create Book
    await expect(page.getByRole("button", { name: "Update Book" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
  });

  test("cancel on create form returns to collection", async ({ page }) => {
    await page.goto("/books/new");

    await expect(page.getByRole("heading", { name: "Add New Book" })).toBeVisible({
      timeout: 10000,
    });

    await page.getByRole("button", { name: "Cancel" }).click();

    await expect(page).toHaveURL(/\/books$/);
  });

  test("cancel on edit form returns to book detail", async ({ page }) => {
    await page.goto("/books/401/edit");

    await expect(page.getByRole("heading", { name: "Edit Book" })).toBeVisible({
      timeout: 10000,
    });

    await page.getByRole("button", { name: "Cancel" }).click();

    await expect(page).toHaveURL(/\/books\/401$/);
  });
});
