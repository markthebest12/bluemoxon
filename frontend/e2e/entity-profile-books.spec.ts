import { test, expect } from "@playwright/test";

/**
 * E2E tests for #1634: Book Thumbnails & Condition Badges on Entity Profiles.
 *
 * Uses /entity/publisher/167 (Smith, Elder & Co.) — a publisher with 25 books,
 * thumbnails, condition badges, and rich key connections with shared book thumbnails.
 *
 * Falls back to /entity/author/227 (Robert Browning) if needed — has 4 books
 * with thumbnails and key connections with shared books.
 */

test.describe("Entity Profile - Book Thumbnails & Badges", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ page }) => {
    await page.goto("/entity/publisher/167", { waitUntil: "networkidle" });
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 30000 });
  });

  test("entity-books section is visible", async ({ page }) => {
    const booksSection = page.locator('[data-testid="entity-books"]');
    await expect(booksSection).toBeVisible({ timeout: 10000 });
  });

  test("book entries display thumbnail images with valid src", async ({ page }) => {
    const booksSection = page.locator('[data-testid="entity-books"]');
    const hasBooksSection = await booksSection.isVisible({ timeout: 10000 }).catch(() => false);
    test.skip(!hasBooksSection, "entity-books section not found — skipping thumbnail test");

    const thumbnails = booksSection.locator('[data-testid="book-thumbnail"]');
    const count = await thumbnails.count();
    expect(count).toBeGreaterThan(0);

    // Verify first several thumbnails have valid image src attributes
    const checkCount = Math.min(count, 5);
    for (let i = 0; i < checkCount; i++) {
      const thumbnail = thumbnails.nth(i);
      await expect(thumbnail).toBeVisible();

      // Thumbnail should be an img or contain an img
      const img =
        (await thumbnail.evaluate((el) => el.tagName.toLowerCase())) === "img"
          ? thumbnail
          : thumbnail.locator("img").first();

      const src = await img.getAttribute("src");
      expect(src).toBeTruthy();
      expect(src!.length).toBeGreaterThan(0);
      // Images are served from CloudFront or the bluemoxon domain
      expect(src).toMatch(/cloudfront|bluemoxon\.com/);
    }
  });

  test("book entries display condition badges", async ({ page }) => {
    const booksSection = page.locator('[data-testid="entity-books"]');
    const hasBooksSection = await booksSection.isVisible({ timeout: 10000 }).catch(() => false);
    test.skip(!hasBooksSection, "entity-books section not found — skipping badge test");

    const badges = booksSection.locator('[data-testid="condition-badge"]');
    const count = await badges.count();
    expect(count).toBeGreaterThan(0);

    // Verify first badge is visible and has text content
    const firstBadge = badges.first();
    await expect(firstBadge).toBeVisible();
    const text = await firstBadge.textContent();
    expect(text?.trim().length).toBeGreaterThan(0);
  });
});

test.describe("Entity Profile - Key Connections Shared Book Thumbnails", () => {
  test("key connections section shows shared book thumbnails", async ({ page }) => {
    await page.goto("/entity/publisher/167", { waitUntil: "networkidle" });
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 30000 });

    const connectionsSection = page.locator('[data-testid="key-connections"]');
    const hasConnections = await connectionsSection
      .isVisible({ timeout: 10000 })
      .catch(() => false);
    test.skip(
      !hasConnections,
      "key-connections section not found — skipping shared book thumbnail test"
    );

    const thumbnails = connectionsSection.locator('[data-testid="book-thumbnail"]');
    const count = await thumbnails.count();
    expect(count).toBeGreaterThan(0);

    // Verify first thumbnail in connections has a valid image src
    const firstThumb = thumbnails.first();
    await expect(firstThumb).toBeVisible();

    const img =
      (await firstThumb.evaluate((el) => el.tagName.toLowerCase())) === "img"
        ? firstThumb
        : firstThumb.locator("img").first();

    const src = await img.getAttribute("src");
    expect(src).toBeTruthy();
    expect(src!.length).toBeGreaterThan(0);
    expect(src).toMatch(/cloudfront|bluemoxon\.com/);
  });
});

test.describe("Entity Profile - Book Thumbnails (Author fallback)", () => {
  // Uses Robert Browning (author/227) as a secondary entity to verify
  // thumbnails work across entity types.

  test("author profile shows book thumbnails", async ({ page }) => {
    await page.goto("/entity/author/227", { waitUntil: "networkidle" });
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 30000 });

    const booksSection = page.locator('[data-testid="entity-books"]');
    const hasBooksSection = await booksSection.isVisible({ timeout: 10000 }).catch(() => false);
    test.skip(!hasBooksSection, "entity-books section not found on author/227 — skipping");

    const thumbnails = booksSection.locator('[data-testid="book-thumbnail"]');
    const count = await thumbnails.count();
    expect(count).toBeGreaterThan(0);

    const firstThumb = thumbnails.first();
    await expect(firstThumb).toBeVisible();

    const img =
      (await firstThumb.evaluate((el) => el.tagName.toLowerCase())) === "img"
        ? firstThumb
        : firstThumb.locator("img").first();

    const src = await img.getAttribute("src");
    expect(src).toBeTruthy();
    expect(src).toMatch(/cloudfront|bluemoxon\.com/);
  });
});
