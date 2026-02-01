import { test, expect } from "@playwright/test";

const viewerRoutes = [
  { path: "/", name: "Dashboard" },
  { path: "/books", name: "Books" },
  { path: "/social-circles", name: "Social Circles" },
  { path: "/stickers", name: "Stickers" },
  { path: "/profile", name: "Profile" },
  { path: "/reports/insurance", name: "Insurance Report" },
];

const adminRoutes = [
  { path: "/admin", name: "Admin" },
  { path: "/admin/acquisitions", name: "Acquisitions" },
];

const editorRoutes = [{ path: "/admin/config", name: "Admin Config" }];

test.describe("Smoke: Viewer routes", () => {
  test.use({ storageState: ".auth/viewer.json" });

  for (const route of viewerRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).not.toHaveURL(/\/login/);
      await expect(page.locator("body")).not.toBeEmpty();
    });
  }

  for (const route of [...adminRoutes, ...editorRoutes]) {
    test(`viewer redirected from ${route.name} (${route.path})`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).toHaveURL("/", { timeout: 15_000 });
    });
  }
});

test.describe("Smoke: Editor routes", () => {
  test.use({ storageState: ".auth/editor.json" });

  for (const route of viewerRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).not.toHaveURL(/\/login/);
      await expect(page.locator("body")).not.toBeEmpty();
    });
  }

  test("editor can access admin config", async ({ page }) => {
    await page.goto("/admin/config");
    await expect(page).not.toHaveURL(/\/login/);
  });
});

test.describe("Smoke: Admin routes", () => {
  test.use({ storageState: ".auth/admin.json" });

  const allRoutes = [...viewerRoutes, ...adminRoutes, ...editorRoutes];

  for (const route of allRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).not.toHaveURL(/\/login/);
      await expect(page.locator("body")).not.toBeEmpty();
    });
  }
});
