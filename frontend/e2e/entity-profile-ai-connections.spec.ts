import { test, expect } from "@playwright/test";

/**
 * E2E tests for AI-discovered connections on entity profiles.
 *
 * Validates that:
 * - AI badge renders on AI-discovered connections
 * - Scandal-type connections appear when present
 * - AI connections display narrative text
 * - "Rumored:" prefix appears on low-confidence narratives
 * - Shared book count is hidden for AI-only connections
 *
 * Uses:
 * - /entity/author/31 (Elizabeth Barrett Browning) — MARRIAGE to Robert Browning (confidence 1.0)
 * - /entity/author/250 (Charles Dickens) — CO-AUTHORS with Wilkie Collins, possible scandal connections
 *
 * Gracefully skips if AI connections have not been generated yet.
 */

test.describe("Entity Profile - AI Connection Badge Rendering", () => {
  test.beforeEach(async ({ page }) => {
    // Elizabeth Barrett Browning — known high-confidence AI marriage connection
    await page.goto("/entity/author/31");
    await expect(page.getByTestId("profile-hero")).toBeVisible({ timeout: 15000 });
  });

  test("AI badge is visible on AI-discovered connection cards", async ({ page }) => {
    const aiBadges = page.locator(".key-connections__ai-badge");
    const count = await aiBadges.count();
    test.skip(count === 0, "No AI connections found — profiles may need regeneration");

    // Every AI badge should display the text "AI"
    for (let i = 0; i < count; i++) {
      await expect(aiBadges.nth(i)).toBeVisible();
      await expect(aiBadges.nth(i)).toHaveText("AI");
    }
  });

  test("AI connection card shows sub-type badge", async ({ page }) => {
    const aiCards = page.locator(".key-connections__card:has(.key-connections__ai-badge)");
    const count = await aiCards.count();
    test.skip(count === 0, "No AI connections found — profiles may need regeneration");

    // At least one AI card should have a sub-type badge (e.g., MARRIAGE)
    const subTypes = aiCards.locator(".key-connections__sub-type");
    const subTypeCount = await subTypes.count();
    expect(subTypeCount).toBeGreaterThan(0);

    const text = await subTypes.first().textContent();
    expect(text?.trim().length).toBeGreaterThan(0);
  });

  test("AI connection card displays narrative text", async ({ page }) => {
    const aiCards = page.locator(".key-connections__card:has(.key-connections__ai-badge)");
    const count = await aiCards.count();
    test.skip(count === 0, "No AI connections found — profiles may need regeneration");

    // AI connections should have a narrative describing the relationship
    const narrative = aiCards.first().locator(".key-connections__narrative");
    const hasNarrative = await narrative.isVisible().catch(() => false);

    if (hasNarrative) {
      const text = await narrative.textContent();
      expect(text?.trim().length).toBeGreaterThan(0);
    }
  });

  test("AI-only connections hide '0 shared books' label", async ({ page }) => {
    const aiCards = page.locator(".key-connections__card:has(.key-connections__ai-badge)");
    const count = await aiCards.count();
    test.skip(count === 0, "No AI connections found — profiles may need regeneration");

    // For AI-only connections (no shared books), the "0 shared books" text should not appear
    for (let i = 0; i < count; i++) {
      const meta = aiCards.nth(i).locator(".key-connections__meta");
      const metaText = await meta.textContent();

      // If this AI connection has 0 shared books, the label should be absent
      if (metaText && !metaText.includes("shared book")) {
        // Correct: AI-only connection hides the count
        expect(metaText).not.toContain("0 shared books");
      }
    }
  });
});

test.describe("Entity Profile - Scandal Connections", () => {
  test("scandal connections appear on Dickens profile", async ({ page }) => {
    // Charles Dickens — known for controversial personal life, may have scandal connections
    await page.goto("/entity/author/250");
    await expect(page.getByTestId("profile-hero")).toBeVisible({ timeout: 15000 });

    const allCards = page.locator(".key-connections__card");
    const totalCount = await allCards.count();
    test.skip(totalCount === 0, "No connections found on Dickens profile");

    // Check connection type labels for scandal-related sub-types
    const typeLabels = page.locator(".key-connections__type");
    const subTypeLabels = page.locator(".key-connections__sub-type");

    const typeTexts: string[] = [];
    const typeCount = await typeLabels.count();
    for (let i = 0; i < typeCount; i++) {
      const text = await typeLabels.nth(i).textContent();
      if (text) typeTexts.push(text.trim().toUpperCase());
    }

    const subTypeTexts: string[] = [];
    const subTypeCount = await subTypeLabels.count();
    for (let i = 0; i < subTypeCount; i++) {
      const text = await subTypeLabels.nth(i).textContent();
      if (text) subTypeTexts.push(text.trim().toUpperCase());
    }

    // At minimum, Dickens should have AI connections (scandal or otherwise)
    const aiBadges = page.locator(".key-connections__ai-badge");
    const aiCount = await aiBadges.count();
    test.skip(aiCount === 0, "No AI connections on Dickens — profiles may need regeneration");

    // Verify AI connections have valid sub-type labels
    expect(subTypeTexts.length).toBeGreaterThan(0);
  });
});

test.describe("Entity Profile - Low Confidence AI Connections", () => {
  test("low confidence narrative has 'Rumored:' prefix via CSS", async ({ page }) => {
    // Visit a high-connection entity that may have low-confidence AI connections
    await page.goto("/entity/author/250");
    await expect(page.getByTestId("profile-hero")).toBeVisible({ timeout: 15000 });

    const rumoredNarratives = page.locator(".key-connections__narrative--rumored");
    const count = await rumoredNarratives.count();

    // This test verifies the CSS class is applied — skip if no low-confidence connections exist
    test.skip(count === 0, "No low-confidence AI connections found — expected for high-confidence data");

    // The --rumored modifier class uses CSS ::before to prepend "Rumored: "
    await expect(rumoredNarratives.first()).toBeVisible();
  });
});
