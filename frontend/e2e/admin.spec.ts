import { test, expect } from "@playwright/test";

// Admin tests require admin-level authentication
test.use({ storageState: ".auth/admin.json" });

test.describe("Admin Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/admin");
  });

  test("displays admin settings heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Admin Settings" })).toBeVisible();
  });

  test("shows users tab by default with user list", async ({ page }) => {
    // Users tab should be active by default
    await expect(page.getByRole("button", { name: "Users" })).toBeVisible();
    await expect(page.getByRole("button", { name: "API Keys" })).toBeVisible();

    // Should show the invite user form
    await expect(page.getByText("Invite New User")).toBeVisible({ timeout: 10000 });
    await expect(page.getByPlaceholder("Email address")).toBeVisible();
    await expect(page.getByRole("button", { name: "Send Invite" })).toBeVisible();
  });

  test("shows role selector options in invite form", async ({ page }) => {
    await expect(page.getByText("Invite New User")).toBeVisible({ timeout: 10000 });

    // Role dropdown should have viewer, editor, admin options
    const roleSelect = page.locator("select").first();
    await expect(roleSelect).toBeVisible();
    await expect(roleSelect.locator("option", { hasText: "Viewer" })).toBeAttached();
    await expect(roleSelect.locator("option", { hasText: "Editor" })).toBeAttached();
    await expect(roleSelect.locator("option", { hasText: "Admin" })).toBeAttached();
  });

  test("can switch to API Keys tab", async ({ page }) => {
    await page.getByRole("button", { name: "API Keys" }).click();

    // Should show the create key form
    await expect(page.getByText("Create New API Key")).toBeVisible();
    await expect(page.getByPlaceholder(/Key name/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Key" })).toBeVisible();
  });

  test("API Keys tab shows table headers", async ({ page }) => {
    await page.getByRole("button", { name: "API Keys" }).click();

    // Table should have expected column headers
    await expect(page.getByRole("columnheader", { name: "Name" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Key Prefix" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Created" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();
  });

  test("user list shows user details after loading", async ({ page }) => {
    // Wait for loading to complete (loading text disappears or users appear)
    await page
      .waitForSelector("text=Loading users...", { state: "hidden", timeout: 10000 })
      .catch(() => {
        // Loading may already be done
      });

    // Should show at least one user with role selector and action buttons
    const userCards = page.locator(".bg-white.rounded-lg.shadow-sm.p-4");
    const userCount = await userCards.count();
    if (userCount > 0) {
      // First user card should have a role dropdown
      const firstUserRole = userCards.first().locator("select");
      await expect(firstUserRole).toBeVisible();
    }
  });
});

test.describe("Acquisitions Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/admin/acquisitions");
  });

  test("displays acquisitions heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Acquisitions" })).toBeVisible();
  });

  test("shows kanban board columns", async ({ page }) => {
    // Wait for loading to complete
    await page.waitForSelector(".skeleton", { state: "hidden", timeout: 10000 }).catch(() => {
      // Skeletons may already be gone
    });

    // Three kanban columns: Evaluating, In Transit, Received
    await expect(page.getByText("Evaluating")).toBeVisible();
    await expect(page.getByText("In Transit")).toBeVisible();
    await expect(page.getByText("Received (30d)")).toBeVisible();
  });

  test("has import and add buttons", async ({ page }) => {
    await expect(page.getByTestId("import-from-ebay")).toBeVisible();
    await expect(page.getByTestId("add-to-watchlist")).toBeVisible();
  });

  test("import from eBay button opens modal", async ({ page }) => {
    await page.getByTestId("import-from-ebay").click();

    // Modal should appear (look for modal overlay or dialog)
    const modal = page.locator(".fixed.inset-0, [role='dialog']");
    await expect(modal.first()).toBeVisible({ timeout: 5000 });
  });

  test("add manually button opens watchlist modal", async ({ page }) => {
    await page.getByTestId("add-to-watchlist").click();

    // Modal should appear
    const modal = page.locator(".fixed.inset-0, [role='dialog']");
    await expect(modal.first()).toBeVisible({ timeout: 5000 });
  });

  test("shows Victorian ornament decoration", async ({ page }) => {
    await expect(page.getByTestId("victorian-ornament")).toBeAttached();
  });
});

test.describe("Admin Config Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/admin/config");
  });

  test("displays admin configuration heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Admin Configuration" })).toBeVisible();
  });

  test("shows tab navigation with all tabs", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Settings" })).toBeVisible();
    await expect(page.getByRole("button", { name: "System Status" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Scoring Config" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reference Data" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Costs" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Maintenance" })).toBeVisible();
  });

  test("settings tab shows currency conversion rates", async ({ page }) => {
    // Settings tab is active by default
    await expect(page.getByText("Currency Conversion Rates")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("GBP to USD")).toBeVisible();
    await expect(page.getByText("EUR to USD")).toBeVisible();
    await expect(page.getByRole("button", { name: "Save" })).toBeVisible();
  });

  test("system status tab loads system info", async ({ page }) => {
    await page.getByRole("button", { name: "System Status" }).click();

    // Should show version and deployment section
    await expect(page.getByText("Version & Deployment")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("App Version")).toBeVisible();
    await expect(page.getByText("Health Checks")).toBeVisible();
  });

  test("system status tab shows health checks", async ({ page }) => {
    await page.getByRole("button", { name: "System Status" }).click();

    await expect(page.getByText("Health Checks")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Database")).toBeVisible();
    await expect(page.getByText("S3 Images")).toBeVisible();
    await expect(page.getByText("Cognito")).toBeVisible();
  });

  test("scoring config tab shows scoring sections", async ({ page }) => {
    await page.getByRole("button", { name: "Scoring Config" }).click();

    await expect(page.getByText("Quality Score Points")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Strategic Fit Points")).toBeVisible();
    await expect(page.getByText("Thresholds")).toBeVisible();
    await expect(page.getByText("Combined Score Weights")).toBeVisible();
  });

  test("reference data tab shows entity sections", async ({ page }) => {
    await page.getByRole("button", { name: "Reference Data" }).click();

    await expect(page.getByRole("heading", { name: "Authors" })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole("heading", { name: "Publishers" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Binders" })).toBeVisible();
  });

  test("maintenance tab shows cleanup tools", async ({ page }) => {
    await page.getByRole("button", { name: "Maintenance" }).click();

    await expect(page.getByText("Cleanup Tools")).toBeVisible();
  });
});
