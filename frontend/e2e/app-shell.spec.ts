import { test, expect } from "@playwright/test";

const RELAXED = !!process.env.E2E_RELAXED_BUDGETS || !!process.env.CI;
const SHELL_TIMEOUT = RELAXED ? 5000 : 2000;
const MOUNT_TIMEOUT = RELAXED ? 15000 : 8000;

test.describe("App Shell Skeleton", () => {
  test("nav bar is visible quickly after navigation start", async ({ page }) => {
    // Measure time from navigation start to nav visibility
    const startTime = Date.now();

    // Start navigation but don't wait for network idle
    await page.goto("/", { waitUntil: "commit" });

    // Check that the app shell nav is visible (timeout varies by environment)
    const navBar = page.locator(".app-shell-nav");
    await expect(navBar).toBeVisible({ timeout: SHELL_TIMEOUT });

    const elapsed = Date.now() - startTime;
    console.log(`App shell nav visible in ${elapsed}ms`);

    // Verify logo image is present
    const logo = navBar.locator(".nav-logo");
    await expect(logo).toBeVisible();
  });

  test("skeleton stat cards are visible before auth completes", async ({ page }) => {
    // Navigate and check skeleton immediately
    await page.goto("/", { waitUntil: "commit" });

    // Skeleton stat cards should be visible
    const skeletonStats = page.locator(".skeleton-stat");
    await expect(skeletonStats.first()).toBeVisible({ timeout: SHELL_TIMEOUT });

    // Should have 4 stat cards (matching HomeView dashboard)
    const statCount = await skeletonStats.count();
    expect(statCount).toBe(4);

    console.log(`Found ${statCount} skeleton stat cards in app shell`);
  });

  test("Vue replaces skeleton when app mounts", async ({ page }) => {
    await page.goto("/");

    // Wait for Vue to mount - the real NavBar should be visible
    // NavBar.vue uses <nav class="bg-victorian-hunter-900...">
    const realNav = page.locator("nav.bg-victorian-hunter-900");
    await expect(realNav).toBeVisible({ timeout: MOUNT_TIMEOUT });

    // App shell nav should no longer be visible (replaced by Vue)
    const appShellNav = page.locator(".app-shell-nav");
    await expect(appShellNav).not.toBeVisible();

    // Skeleton elements should be gone
    const skeletonStats = page.locator(".skeleton-stat");
    await expect(skeletonStats).not.toBeVisible();

    // Real navigation links should be present
    await expect(page.getByRole("link", { name: /Dashboard/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Collection/i })).toBeVisible();
  });

  test("skeleton provides seamless transition to real content", async ({ page }) => {
    // This test verifies there's no visible flash or jarring transition
    // by checking that either skeleton OR real content is always visible

    await page.goto("/", { waitUntil: "commit" });

    // At any point after commit, we should have SOME nav visible
    // Either the app shell nav OR the real Vue nav
    const anyNav = page.locator(".app-shell-nav, nav.bg-victorian-hunter-900");
    await expect(anyNav.first()).toBeVisible({ timeout: SHELL_TIMEOUT });

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
    await expect(appShellNav).toBeVisible({ timeout: SHELL_TIMEOUT });

    // Check nav container and logo
    const navContainer = appShellNav.locator(".nav-container");
    await expect(navContainer).toBeVisible();

    const logo = appShellNav.locator(".nav-logo");
    await expect(logo).toBeVisible();

    // Check skeleton main area
    const skeletonMain = page.locator(".app-shell-main");
    await expect(skeletonMain).toBeVisible();

    // Check skeleton header
    const skeletonHeader = page.locator(".skeleton-header");
    await expect(skeletonHeader).toBeVisible();

    // Check stat cards grid
    const skeletonStats = page.locator(".skeleton-stats");
    await expect(skeletonStats).toBeVisible();

    // Check link cards grid
    const skeletonLinks = page.locator(".skeleton-links");
    await expect(skeletonLinks).toBeVisible();
  });

  test("nav links are hidden on mobile viewport", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto("/", { waitUntil: "commit" });

    // Nav bar should be visible
    const navBar = page.locator(".app-shell-nav");
    await expect(navBar).toBeVisible({ timeout: SHELL_TIMEOUT });

    // Nav links should be hidden on mobile (display: none below md breakpoint)
    const navLinks = page.locator(".nav-links");
    await expect(navLinks).not.toBeVisible();
  });
});
