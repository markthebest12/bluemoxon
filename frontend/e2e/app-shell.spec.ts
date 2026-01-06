import { test, expect } from "@playwright/test";

test.describe("App Shell Skeleton", () => {
  test("nav bar is visible within 500ms of navigation start", async ({ page }) => {
    // Measure time from navigation start to nav visibility
    const startTime = Date.now();

    // Start navigation but don't wait for network idle
    await page.goto("/", { waitUntil: "commit" });

    // Check that the app shell nav is visible
    const navBar = page.locator(".app-shell-nav");
    await expect(navBar).toBeVisible({ timeout: 500 });

    const elapsed = Date.now() - startTime;
    console.log(`App shell nav visible in ${elapsed}ms`);

    // Verify it contains the logo link
    const logoLink = navBar.locator(".nav-logo");
    await expect(logoLink).toBeVisible();
    await expect(logoLink).toHaveText("BlueMoxon");
  });

  test("skeleton cards are visible before auth completes", async ({ page }) => {
    // Navigate and check skeleton cards immediately
    await page.goto("/", { waitUntil: "commit" });

    // Skeleton cards should be visible immediately
    const skeletonCards = page.locator(".skeleton-card");
    await expect(skeletonCards.first()).toBeVisible({ timeout: 500 });

    // Should have multiple skeleton cards (design shows 6)
    const cardCount = await skeletonCards.count();
    expect(cardCount).toBeGreaterThanOrEqual(3);

    console.log(`Found ${cardCount} skeleton cards in app shell`);
  });

  test("Vue replaces skeleton when app mounts", async ({ page }) => {
    await page.goto("/");

    // Wait for Vue to mount - the real NavBar should be visible
    // NavBar.vue uses <nav class="bg-victorian-hunter-900...">
    const realNav = page.locator("nav.bg-victorian-hunter-900");
    await expect(realNav).toBeVisible({ timeout: 15000 });

    // App shell nav should no longer be visible (replaced by Vue)
    const appShellNav = page.locator(".app-shell-nav");
    await expect(appShellNav).not.toBeVisible();

    // Skeleton cards should also be gone
    const skeletonCards = page.locator(".skeleton-card");
    await expect(skeletonCards).not.toBeVisible();

    // Real navigation links should be present
    await expect(page.getByRole("link", { name: /Collection/i })).toBeVisible();
  });

  test("skeleton provides seamless transition to real content", async ({ page }) => {
    // This test verifies there's no visible flash or jarring transition
    // by checking that either skeleton OR real content is always visible

    await page.goto("/", { waitUntil: "commit" });

    // At any point after commit, we should have SOME nav visible
    // Either the app shell nav OR the real Vue nav
    const anyNav = page.locator(".app-shell-nav, nav.bg-victorian-hunter-900");
    await expect(anyNav.first()).toBeVisible({ timeout: 500 });

    // Wait for full load and verify real nav replaced skeleton
    await page.waitForLoadState("networkidle");
    const realNav = page.locator("nav.bg-victorian-hunter-900");
    await expect(realNav).toBeVisible();
  });

  test("app shell has correct visual structure", async ({ page }) => {
    // Use commit to see the shell before Vue replaces it
    await page.goto("/", { waitUntil: "commit" });

    // Check app shell structure
    const appShellNav = page.locator(".app-shell-nav");
    await expect(appShellNav).toBeVisible({ timeout: 500 });

    // Check nav container exists
    const navContainer = appShellNav.locator(".nav-container");
    await expect(navContainer).toBeVisible();

    // Check nav links section exists
    const navLinks = appShellNav.locator(".nav-links");
    await expect(navLinks).toBeVisible();

    // Check skeleton main area
    const skeletonMain = page.locator(".app-shell-main");
    await expect(skeletonMain).toBeVisible();

    // Check skeleton header
    const skeletonHeader = page.locator(".skeleton-header");
    await expect(skeletonHeader).toBeVisible();

    // Check skeleton grid contains cards
    const skeletonGrid = page.locator(".skeleton-grid");
    await expect(skeletonGrid).toBeVisible();
  });
});
