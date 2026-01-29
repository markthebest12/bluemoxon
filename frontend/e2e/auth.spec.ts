import { test, expect } from "@playwright/test";

test.describe("Unauthenticated access", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("protected route redirects to login with redirect param", async ({ page }) => {
    await page.goto("/books");
    await expect(page).toHaveURL(/\/login\?redirect=/);
  });

  test("home route redirects to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("admin route redirects to login", async ({ page }) => {
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/login/);
  });

  test("profile route redirects to login", async ({ page }) => {
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Login page", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("login form is visible with email and password fields", async ({ page }) => {
    await page.goto("/login");

    await expect(page.getByRole("heading", { name: "BlueMoxon" })).toBeVisible();
    await expect(page.getByText("Sign in to your account")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign In" })).toBeVisible();
    await expect(page.getByText("Contact administrator for access")).toBeVisible();
  });

  test("email field has correct type and placeholder", async ({ page }) => {
    await page.goto("/login");

    const emailInput = page.getByLabel("Email");
    await expect(emailInput).toHaveAttribute("type", "email");
    await expect(emailInput).toHaveAttribute("placeholder", "you@example.com");
  });

  test("password field has correct type", async ({ page }) => {
    await page.goto("/login");

    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toHaveAttribute("type", "password");
  });

  test("login page preserves redirect query param in URL", async ({ page }) => {
    await page.goto("/login?redirect=/books/42");
    await expect(page).toHaveURL(/\/login\?redirect=.*books/);
    await expect(page.getByLabel("Email")).toBeVisible();
  });
});

test.describe("Viewer role guards", () => {
  test.use({ storageState: ".auth/viewer.json" });

  test("viewer can access home page", async ({ page }) => {
    await page.goto("/");
    await expect(page).not.toHaveURL(/\/login/);
  });

  test("viewer can access books page", async ({ page }) => {
    await page.goto("/books");
    await expect(page).toHaveURL(/\/books/);
  });

  test("viewer cannot access /admin - redirects to home", async ({ page }) => {
    await page.goto("/admin");
    await expect(page).not.toHaveURL(/\/admin/);
    await expect(page).toHaveURL("/");
  });

  test("viewer cannot access /admin/config - redirects to home", async ({ page }) => {
    await page.goto("/admin/config");
    await expect(page).not.toHaveURL(/\/admin\/config/);
    await expect(page).toHaveURL("/");
  });

  test("viewer cannot access /admin/acquisitions - redirects to home", async ({ page }) => {
    await page.goto("/admin/acquisitions");
    await expect(page).not.toHaveURL(/\/admin\/acquisitions/);
    await expect(page).toHaveURL("/");
  });
});

test.describe("Editor role guards", () => {
  test.use({ storageState: ".auth/editor.json" });

  test("editor can access /admin/config", async ({ page }) => {
    await page.goto("/admin/config");
    await expect(page).toHaveURL(/\/admin\/config/);
  });

  test("editor cannot access /admin - redirects to home", async ({ page }) => {
    await page.goto("/admin");
    await expect(page).not.toHaveURL(/\/admin$/);
    await expect(page).toHaveURL("/");
  });

  test("editor cannot access /admin/acquisitions - redirects to home", async ({ page }) => {
    await page.goto("/admin/acquisitions");
    await expect(page).not.toHaveURL(/\/admin\/acquisitions/);
    await expect(page).toHaveURL("/");
  });

  test("editor can access books page", async ({ page }) => {
    await page.goto("/books");
    await expect(page).toHaveURL(/\/books/);
  });
});

test.describe("Admin role access", () => {
  test.use({ storageState: ".auth/admin.json" });

  test("admin can access /admin", async ({ page }) => {
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/admin$/);
  });

  test("admin can access /admin/config", async ({ page }) => {
    await page.goto("/admin/config");
    await expect(page).toHaveURL(/\/admin\/config/);
  });

  test("admin can access /admin/acquisitions", async ({ page }) => {
    await page.goto("/admin/acquisitions");
    await expect(page).toHaveURL(/\/admin\/acquisitions/);
  });

  test("admin can access books page", async ({ page }) => {
    await page.goto("/books");
    await expect(page).toHaveURL(/\/books/);
  });

  test("admin can access home page", async ({ page }) => {
    await page.goto("/");
    await expect(page).not.toHaveURL(/\/login/);
  });
});
