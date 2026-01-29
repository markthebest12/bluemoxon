import { test, expect } from "@playwright/test";

test.use({ storageState: ".auth/viewer.json" });

test.describe("Profile Page", () => {
  test("loads profile page without redirect to login", async ({ page }) => {
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/profile/);
    await expect(page.getByRole("heading", { name: "Profile Settings", level: 1 })).toBeVisible();
  });

  test("displays profile information section", async ({ page }) => {
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "Profile Information" })).toBeVisible();
  });

  test("shows first name and last name fields", async ({ page }) => {
    await page.goto("/profile");
    const firstNameInput = page.getByLabel("First Name");
    const lastNameInput = page.getByLabel("Last Name");
    await expect(firstNameInput).toBeVisible();
    await expect(lastNameInput).toBeVisible();
  });

  test("displays user email", async ({ page }) => {
    await page.goto("/profile");
    const emailLabel = page.getByText("Email");
    await expect(emailLabel).toBeVisible();
    // The email value should be displayed next to the label
    const emailDefinition = page.locator("dt", { hasText: "Email" });
    await expect(emailDefinition).toBeVisible();
    // The dd sibling should contain an email-like value
    const emailValue = emailDefinition.locator("+ dd");
    await expect(emailValue).toBeVisible();
    await expect(emailValue).not.toBeEmpty();
  });

  test("displays user role", async ({ page }) => {
    await page.goto("/profile");
    const roleLabel = page.locator("dt", { hasText: "Role" });
    await expect(roleLabel).toBeVisible();
    const roleValue = roleLabel.locator("+ dd");
    await expect(roleValue).toBeVisible();
    await expect(roleValue).not.toBeEmpty();
  });

  test("has save profile button", async ({ page }) => {
    await page.goto("/profile");
    const saveButton = page.getByRole("button", { name: "Save Profile" });
    await expect(saveButton).toBeVisible();
    await expect(saveButton).toBeEnabled();
  });

  test("displays change password section", async ({ page }) => {
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "Change Password" })).toBeVisible();
    await expect(page.getByLabel("Current Password")).toBeVisible();
    await expect(page.getByLabel("New Password", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm New Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Change Password" })).toBeVisible();
  });

  test("displays security section with TOTP status", async ({ page }) => {
    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "Security" })).toBeVisible();
    await expect(page.getByText("Two-factor authentication enabled (TOTP)")).toBeVisible();
  });
});
