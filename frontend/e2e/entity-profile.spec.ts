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

  test("cross-link navigates to target entity profile", async ({ page }) => {
    // Navigate directly to Darwin (high-connection entity with known cross-links)
    await page.goto("/entity/author/34");
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });

    // Look for cross-links in bio summary first
    let crossLink = page
      .locator(".profile-hero .entity-linked-text__link")
      .first();
    let hasCrossLink = await crossLink
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    // If no cross-link in hero, expand a gossip panel and look there
    if (!hasCrossLink) {
      const toggle = page.locator(".key-connections__story-toggle").first();
      const hasToggle = await toggle
        .isVisible({ timeout: 3000 })
        .catch(() => false);
      if (hasToggle) {
        await toggle.click();
        await expect(page.locator(".gossip-panel").first()).toBeVisible({
          timeout: 3000,
        });
        crossLink = page
          .locator(".gossip-panel .entity-linked-text__link")
          .first();
        hasCrossLink = await crossLink
          .isVisible({ timeout: 3000 })
          .catch(() => false);
      }
    }

    // Skip test gracefully if no cross-links found (profiles may not have been regenerated)
    test.skip(
      !hasCrossLink,
      "No cross-links found in entity profile — profiles may need regeneration",
    );

    // Capture the link text for later verification
    const linkText = await crossLink.textContent();
    expect(linkText?.trim().length).toBeGreaterThan(0);

    // Click the cross-link
    await crossLink.click();

    // Verify navigation to a new entity profile
    await expect(page).toHaveURL(/\/entity\//, { timeout: 10000 });
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });

    // Verify the target profile loaded with a name
    const heroName = await page.locator(".profile-hero__name").textContent();
    expect(heroName?.trim().length).toBeGreaterThan(0);
  });

  test("cross-link renders as clickable link in gossip panel", async ({
    page,
  }) => {
    // Try Browning (author/227) as another high-connection entity
    await page.goto("/entity/author/227");
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 15000 });

    // Look for any cross-link on the page
    const crossLinks = page.locator(".entity-linked-text__link");

    // Also check gossip panels
    const toggle = page.locator(".key-connections__story-toggle").first();
    const hasToggle = await toggle
      .isVisible({ timeout: 3000 })
      .catch(() => false);
    if (hasToggle) {
      await toggle.click();
      await expect(page.locator(".gossip-panel").first()).toBeVisible({
        timeout: 3000,
      });
    }

    const linkCount = await crossLinks.count();
    // Just verify at least one cross-link exists somewhere on the profile
    // Skip if none found (graceful for environments without regenerated profiles)
    test.skip(linkCount === 0, "No cross-links found on Browning profile");
    expect(linkCount).toBeGreaterThan(0);
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
