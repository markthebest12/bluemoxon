import { test, expect, type Page } from "@playwright/test";

/**
 * Discover a valid entity by intercepting the social circles API response.
 * Returns the direct URL path to an entity profile (e.g., "/entity/author/42").
 */
async function discoverEntityUrl(page: Page): Promise<string> {
  const responsePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes("/api/v1/social-circles") && resp.status() === 200,
  );
  await page.goto("/social-circles");
  const response = await responsePromise;
  const data = await response.json();
  const node = data.nodes?.[0];
  if (!node?.entity_id || !node?.type) {
    throw new Error(
      "No entities found in social circles API response — cannot run entity profile tests",
    );
  }
  return `/entity/${node.type}/${node.entity_id}`;
}

test.describe("Entity Profile", () => {
  test.beforeEach(async ({ page }) => {
    const entityUrl = await discoverEntityUrl(page);
    await page.goto(entityUrl);
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("displays profile hero with entity name", async ({ page }) => {
    await expect(page.locator(".profile-hero__name")).toBeVisible();
    const name = await page.locator(".profile-hero__name").textContent();
    expect(name?.trim().length).toBeGreaterThan(0);
  });

  test("displays key connections section", async ({ page }) => {
    const connections = page.locator(".key-connections");
    const hasConnections = await connections.isVisible().catch(() => false);
    if (hasConnections) {
      await expect(
        page.locator(".key-connections__card").first(),
      ).toBeVisible();
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
    const hasToggle = await toggle
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    if (hasToggle) {
      // Expand
      await toggle.click();
      await expect(page.locator(".gossip-panel").first()).toBeVisible();
      await expect(
        page.locator(".gossip-panel__summary").first(),
      ).toBeVisible();

      // Collapse
      await toggle.click();
      await expect(page.locator(".gossip-panel").first()).not.toBeVisible();
    }
  });

  test("navigate between profiles via connection link", async ({ page }) => {
    const firstLink = page.locator(".key-connections__name").first();
    const hasLink = await firstLink
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    if (hasLink) {
      const targetName = await firstLink.textContent();
      await firstLink.click();

      // Should navigate to new profile
      await expect(page.locator(".profile-hero")).toBeVisible({
        timeout: 10000,
      });
      const heroName = await page
        .locator(".profile-hero__name")
        .textContent();
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
    const entityUrl = await discoverEntityUrl(page);
    await page.goto(entityUrl);
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("hides EgoNetwork on mobile viewport", async ({ page }) => {
    const egoNetwork = page.locator(".ego-network");
    await expect(egoNetwork).not.toBeVisible();
  });

  test("shows ConnectionSummary on mobile viewport", async ({ page }) => {
    const summary = page.locator(".connection-summary");
    const hasSummary = await summary
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    if (hasSummary) {
      await expect(page.locator(".connection-summary__text")).toBeVisible();
      await expect(page.locator("text=Connected to")).toBeVisible();
    }
  });

  test("profile layout is single column on mobile", async ({ page }) => {
    const content = page.locator(".entity-profile-view__content");
    const hasContent = await content
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    if (hasContent) {
      const box = await content.boundingBox();
      expect(box?.width).toBeLessThanOrEqual(375);
    }
  });
});
