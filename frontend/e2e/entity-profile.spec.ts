import { test, expect } from "@playwright/test";

test.describe("Entity Profile", () => {
  // Navigate to a profile by going through social circles
  // This ensures the route works end-to-end
  test.beforeEach(async ({ page }) => {
    // Go to social circles and click into the first available profile
    await page.goto("/social-circles");
    await expect(page.locator("text=Social Circles")).toBeVisible({ timeout: 15000 });

    // Click the first node card or entity link that appears
    const profileLink = page.locator("a[href*='/entity/']").first();
    await expect(profileLink).toBeVisible({ timeout: 10000 });
    await profileLink.click();
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 10000 });
  });

  test("displays profile hero with entity name", async ({ page }) => {
    await expect(page.locator(".profile-hero__name")).toBeVisible();
    const name = await page.locator(".profile-hero__name").textContent();
    expect(name?.trim().length).toBeGreaterThan(0);
  });

  test("displays key connections section", async ({ page }) => {
    // Key connections may or may not exist depending on the entity
    const connections = page.locator(".key-connections");
    const hasConnections = await connections.isVisible().catch(() => false);
    if (hasConnections) {
      await expect(page.locator(".key-connections__card").first()).toBeVisible();
    }
  });

  test("displays collection stats", async ({ page }) => {
    const stats = page.locator(".collection-stats");
    const hasStats = await stats.isVisible().catch(() => false);
    if (hasStats) {
      await expect(page.locator("text=Total Books")).toBeVisible();
    }
  });

  test("gossip panel expands and collapses", async ({ page }) => {
    const toggle = page.locator(".key-connections__story-toggle").first();
    const hasToggle = await toggle.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasToggle) {
      // Expand
      await toggle.click();
      await expect(page.locator(".gossip-panel").first()).toBeVisible();
      await expect(page.locator(".gossip-panel__summary").first()).toBeVisible();

      // Collapse
      await toggle.click();
      await expect(page.locator(".gossip-panel").first()).not.toBeVisible();
    }
  });

  test("navigate between profiles via connection link", async ({ page }) => {
    const firstLink = page.locator(".key-connections__name").first();
    const hasLink = await firstLink.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasLink) {
      const targetName = await firstLink.textContent();
      await firstLink.click();

      // Should navigate to new profile
      await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 10000 });
      const heroName = await page.locator(".profile-hero__name").textContent();
      expect(heroName?.trim()).toBe(targetName?.trim());
    }
  });

  test("back link returns to social circles", async ({ page }) => {
    await page.locator(".entity-profile-view__back").click();
    await expect(page).toHaveURL(/\/social-circles/);
  });
});

test.describe("Entity Profile - Mobile", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test.beforeEach(async ({ page }) => {
    await page.goto("/social-circles");
    await expect(page.locator("text=Social Circles")).toBeVisible({ timeout: 15000 });

    const profileLink = page.locator("a[href*='/entity/']").first();
    await expect(profileLink).toBeVisible({ timeout: 10000 });
    await profileLink.click();
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 10000 });
  });

  test("hides EgoNetwork on mobile viewport", async ({ page }) => {
    // EgoNetwork canvas should not be visible at mobile width
    const egoNetwork = page.locator(".ego-network");
    await expect(egoNetwork).not.toBeVisible();
  });

  test("shows ConnectionSummary on mobile viewport", async ({ page }) => {
    const summary = page.locator(".connection-summary");
    const hasSummary = await summary.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasSummary) {
      await expect(page.locator(".connection-summary__text")).toBeVisible();
      await expect(page.locator("text=Connected to")).toBeVisible();
    }
  });

  test("profile layout is single column on mobile", async ({ page }) => {
    const content = page.locator(".entity-profile-view__content");
    const hasContent = await content.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasContent) {
      const box = await content.boundingBox();
      // Single column should be less than viewport width with padding
      expect(box?.width).toBeLessThanOrEqual(375);
    }
  });
});
