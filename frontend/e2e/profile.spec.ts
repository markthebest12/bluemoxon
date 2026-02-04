import { test, expect } from "@playwright/test";

test.use({ storageState: ".auth/viewer.json" });

test.describe("Profile Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/profile");
    // Wait for auth store to hydrate and profile to render
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
    // Wait for auth-dependent data: email dd must contain an email address
    const emailDefinition = page.locator("dt", { hasText: "Email" });
    await expect(emailDefinition).toBeVisible();
    const emailValue = emailDefinition.locator("+ dd");
    // Use extended timeout and regex to wait for auth store to populate
    await expect(emailValue).toHaveText(/\S+@\S+\.\S+/, { timeout: 10000 });
  });

  test("displays user role", async ({ page }) => {
    const roleLabel = page.locator("dt", { hasText: "Role" });
    await expect(roleLabel).toBeVisible();
    const roleValue = roleLabel.locator("+ dd");
    // Use extended timeout to wait for auth store to populate role
    await expect(roleValue).toHaveText(/.+/, { timeout: 10000 });
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
