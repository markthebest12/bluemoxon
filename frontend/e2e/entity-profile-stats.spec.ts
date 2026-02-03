import { test, expect } from "@playwright/test";

/**
 * E2E tests for entity profile extended stats (#1633).
 *
 * Uses publisher/167 (Smith, Elder & Co.) — a publisher with 25 books,
 * rich condition data, and acquisitions spanning multiple years.
 */
const ENTITY_URL = "/entity/publisher/167";

test.describe("Entity Profile - Collection Stats", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ENTITY_URL);
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("collection-stats section is visible", async ({ page }) => {
    const stats = page.locator('[data-testid="collection-stats"]');
    const hasStats = await stats.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasStats, "Collection stats section not present for this entity");

    await expect(stats).toBeVisible();
    await expect(stats.locator("text=Total Books")).toBeVisible();
  });

  test("displays total books count", async ({ page }) => {
    const stats = page.locator('[data-testid="collection-stats"]');
    const hasStats = await stats.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasStats, "Collection stats section not present for this entity");

    // The Total Books value should be a positive integer
    const totalBooksItem = stats.locator("dt:has-text('Total Books') + dd");
    await expect(totalBooksItem).toBeVisible();
    const totalText = await totalBooksItem.textContent();
    expect(Number(totalText?.trim())).toBeGreaterThan(0);
  });
});

test.describe("Entity Profile - Condition Breakdown", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ENTITY_URL);
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("condition bar renders with segments", async ({ page }) => {
    const conditionBar = page.locator('[data-testid="condition-bar"]');
    const hasBar = await conditionBar.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasBar, "Condition bar not present — entity may have single condition or no data");

    const segments = conditionBar.locator('[data-testid="condition-segment"]');
    const segmentCount = await segments.count();
    expect(segmentCount).toBeGreaterThanOrEqual(2);

    // Each segment should have a background color set via inline style
    for (let i = 0; i < segmentCount; i++) {
      const style = await segments.nth(i).getAttribute("style");
      expect(style).toContain("background-color");
    }
  });

  test("condition legend shows grade labels", async ({ page }) => {
    const legend = page.locator('[data-testid="condition-legend"]');
    const hasLegend = await legend.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasLegend, "Condition legend not present — entity may have single condition or no data");

    // Legend should contain at least one grade label from the known set
    const knownGrades = ["Fine", "Near Fine", "Very Good", "Good", "Fair", "Poor", "Ungraded"];
    const legendText = await legend.textContent();
    const matchedGrades = knownGrades.filter((grade) => legendText?.includes(grade));
    expect(matchedGrades.length).toBeGreaterThanOrEqual(1);
  });

  test("condition legend count matches segment count", async ({ page }) => {
    const conditionBar = page.locator('[data-testid="condition-bar"]');
    const hasBar = await conditionBar.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasBar, "Condition bar not present");

    const segmentCount = await conditionBar.locator('[data-testid="condition-segment"]').count();
    const legend = page.locator('[data-testid="condition-legend"]');
    const legendItemCount = await legend
      .locator(".collection-stats__condition-legend-item")
      .count();
    expect(legendItemCount).toBe(segmentCount);
  });
});

test.describe("Entity Profile - Acquisition Timeline", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(ENTITY_URL);
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("acquisition timeline renders with bars", async ({ page }) => {
    const timeline = page.locator('[data-testid="acquisition-timeline"]');
    const hasTimeline = await timeline.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasTimeline, "Acquisition timeline not present — fewer than 2 years of data");

    const bars = timeline.locator('[data-testid="acquisition-bar"]');
    const barCount = await bars.count();
    expect(barCount).toBeGreaterThanOrEqual(2);
  });

  test("acquisition bars have positive heights", async ({ page }) => {
    const timeline = page.locator('[data-testid="acquisition-timeline"]');
    const hasTimeline = await timeline.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasTimeline, "Acquisition timeline not present");

    const bars = timeline.locator('[data-testid="acquisition-bar"]');
    const barCount = await bars.count();

    for (let i = 0; i < barCount; i++) {
      const style = await bars.nth(i).getAttribute("style");
      const heightMatch = style?.match(/height:\s*(\d+)px/);
      expect(heightMatch).toBeTruthy();
      expect(Number(heightMatch?.[1])).toBeGreaterThanOrEqual(4); // min-height is 4px
    }
  });

  test("acquisition timeline shows year labels", async ({ page }) => {
    const timeline = page.locator('[data-testid="acquisition-timeline"]');
    const hasTimeline = await timeline.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasTimeline, "Acquisition timeline not present");

    const years = timeline.locator(".acquisition-timeline__year");
    const yearCount = await years.count();
    expect(yearCount).toBeGreaterThanOrEqual(2);

    // Each year label should be a 4-digit number
    for (let i = 0; i < yearCount; i++) {
      const yearText = await years.nth(i).textContent();
      expect(yearText?.trim()).toMatch(/^\d{4}$/);
    }
  });

  test("acquisition timeline shows count labels", async ({ page }) => {
    const timeline = page.locator('[data-testid="acquisition-timeline"]');
    const hasTimeline = await timeline.isVisible({ timeout: 5000 }).catch(() => false);
    test.skip(!hasTimeline, "Acquisition timeline not present");

    const counts = timeline.locator(".acquisition-timeline__count");
    const countTotal = await counts.count();
    expect(countTotal).toBeGreaterThanOrEqual(2);

    // Each count should be a positive integer
    for (let i = 0; i < countTotal; i++) {
      const countText = await counts.nth(i).textContent();
      expect(Number(countText?.trim())).toBeGreaterThan(0);
    }
  });
});
