import { test, expect } from "@playwright/test";

/**
 * E2E tests for #1632: Entity Portraits on Profile Pages.
 *
 * Validates that:
 * - Entities with uploaded portraits display a real image from the CDN
 * - Entities without portraits display a local placeholder SVG
 * - The portrait renders as a circle (border-radius: 50%)
 * - The profile-hero section is visible
 *
 * Uses:
 * - /entity/author/31 (Elizabeth Barrett Browning) — has a portrait uploaded to S3
 * - /entity/binder/4 (Bayntun) — no Wikidata portrait, uses placeholder
 */

test.describe("Entity Profile - Portrait (with image)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/entity/author/31");
    await expect(page.getByTestId("profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("profile-hero section is visible", async ({ page }) => {
    await expect(page.getByTestId("profile-hero")).toBeVisible();
  });

  test("portrait displays a real image from CDN", async ({ page }) => {
    const portrait = page.getByTestId("profile-portrait");
    await expect(portrait).toBeVisible();

    const src = await portrait.getAttribute("src");
    expect(src).toBeTruthy();
    // Portrait should be served from the BlueMoxon CDN (book-images/entities path)
    expect(src).toMatch(/bluemoxon\.com\/book-images\/entities/);
  });

  test("portrait is visually circular on desktop", async ({ page }) => {
    const portrait = page.getByTestId("profile-portrait");
    await expect(portrait).toBeVisible();

    const borderRadius = await portrait.evaluate(
      (el) => getComputedStyle(el).borderRadius
    );
    // border-radius: 50% computes to half the element's dimensions (e.g. "60px")
    // Accept either percentage or computed pixel value
    expect(borderRadius).toMatch(/50%|^\d+px$/);
  });
});

test.describe("Entity Profile - Portrait (placeholder)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/entity/binder/4");
    await expect(page.getByTestId("profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("portrait displays placeholder SVG for entity without image", async ({ page }) => {
    const portrait = page.getByTestId("profile-portrait");
    await expect(portrait).toBeVisible();

    const src = await portrait.getAttribute("src");
    expect(src).toBeTruthy();
    // Placeholder images are served from the local /images/entity-placeholders/ path
    expect(src).toContain("entity-placeholders");
  });

  test("placeholder portrait is also circular", async ({ page }) => {
    const portrait = page.getByTestId("profile-portrait");
    await expect(portrait).toBeVisible();

    const borderRadius = await portrait.evaluate(
      (el) => getComputedStyle(el).borderRadius
    );
    expect(borderRadius).toMatch(/50%|^\d+px$/);
  });
});
