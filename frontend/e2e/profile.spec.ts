import { test, expect } from "@playwright/test";

test.use({ storageState: ".auth/viewer.json" });

test.describe("Profile Page", () => {
  test.beforeEach(async ({ page }) => {
    // Set up response listener BEFORE navigating so we capture the auth API call.
    // The /users/me call is the definitive signal that auth store hydration is
    // complete — email, role, and name are all populated after it resolves.
    const usersMe = page.waitForResponse(
      (resp) => resp.url().includes("/api/v1/users/me") && resp.status() === 200,
    );
    await page.goto("/profile");
    await usersMe;
    // Wait for profile to render (heading is inside the v-else branch that only
    // appears after authInitializing becomes false)
    await expect(
      page.getByRole("heading", { name: "Profile Settings", level: 1 }),
    ).toBeVisible({ timeout: 15000 });
  });

  test("loads profile page without redirect to login", async ({ page }) => {
    await expect(page).toHaveURL(/\/profile/);
    await expect(page.getByRole("heading", { name: "Profile Settings", level: 1 })).toBeVisible();
  });

  test("displays profile information section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Profile Information" })).toBeVisible();
  });

  test("shows first name and last name fields", async ({ page }) => {
    const firstNameInput = page.getByLabel("First Name");
    const lastNameInput = page.getByLabel("Last Name");
    await expect(firstNameInput).toBeVisible();
    await expect(lastNameInput).toBeVisible();
  });

  test("displays user email", async ({ page }) => {
    // Auth hydration is guaranteed complete by beforeEach (waitForResponse on /users/me).
    // The email is rendered from authStore.user?.email which is set during checkAuth().
    const emailDefinition = page.locator("dt", { hasText: "Email" });
    await expect(emailDefinition).toBeVisible();
    const emailValue = emailDefinition.locator("+ dd");
    await expect(emailValue).toHaveText(/\S+@\S+\.\S+/, { timeout: 15000 });
  });

  test("displays user role", async ({ page }) => {
    // Auth hydration is guaranteed complete by beforeEach (waitForResponse on /users/me).
    const roleLabel = page.locator("dt", { hasText: "Role" });
    await expect(roleLabel).toBeVisible();
    const roleValue = roleLabel.locator("+ dd");
    await expect(roleValue).toHaveText(/.+/, { timeout: 15000 });
  });

  test("has save profile button", async ({ page }) => {
    const saveButton = page.getByRole("button", { name: "Save Profile" });
    await expect(saveButton).toBeVisible();
    await expect(saveButton).toBeEnabled();
  });

  test("displays change password section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Change Password" })).toBeVisible();
    await expect(page.getByLabel("Current Password")).toBeVisible();
    await expect(page.getByLabel("New Password", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm New Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Change Password" })).toBeVisible();
  });

  test("displays security section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Security" })).toBeVisible();
    // Verify the security section contains authentication-related content
    // without coupling to specific TOTP infra state
    const securitySection = page.getByRole("heading", { name: "Security" }).locator("..");
    await expect(securitySection).toContainText(/authentication/i);
  });
});
