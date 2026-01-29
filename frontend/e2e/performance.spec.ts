import { test, expect, type Page } from "@playwright/test";

const RELAXED = !!process.env.E2E_RELAXED_BUDGETS;
const FCP_BUDGET = RELAXED ? 5000 : 2500;
const DCL_BUDGET = RELAXED ? 6000 : 3000;
const BOOKS_FCP_BUDGET = RELAXED ? 6000 : 3000;

interface PerformanceMetrics {
  // Navigation timing
  domContentLoaded: number;
  domComplete: number;
  loadComplete: number;
  // Paint timing
  firstPaint: number | null;
  firstContentfulPaint: number | null;
  // Core Web Vitals
  largestContentfulPaint: number | null;
  // Resource metrics
  totalResources: number;
  totalTransferSize: number;
  jsResources: number;
  jsTransferSize: number;
  cssResources: number;
  cssTransferSize: number;
  imageResources: number;
  imageTransferSize: number;
}

async function measurePerformance(page: Page): Promise<PerformanceMetrics> {
  // Get navigation timing
  const navigationTiming = await page.evaluate(() => {
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
    return {
      domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
      domComplete: nav.domComplete - nav.startTime,
      loadComplete: nav.loadEventEnd - nav.startTime,
    };
  });

  // Get paint timing
  const paintTiming = await page.evaluate(() => {
    const paints = performance.getEntriesByType("paint");
    const fp = paints.find((p) => p.name === "first-paint");
    const fcp = paints.find((p) => p.name === "first-contentful-paint");
    return {
      firstPaint: fp ? fp.startTime : null,
      firstContentfulPaint: fcp ? fcp.startTime : null,
    };
  });

  // Get LCP
  const lcp = await page.evaluate(() => {
    return new Promise((resolve) => {
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        resolve(lastEntry ? lastEntry.startTime : null);
      }).observe({ type: "largest-contentful-paint", buffered: true });
      // Fallback timeout
      setTimeout(() => resolve(null), 5000);
    });
  });

  // Get resource timing
  const resourceTiming = await page.evaluate(() => {
    const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
    const jsResources = resources.filter((r) => r.initiatorType === "script");
    const cssResources = resources.filter(
      (r) => r.initiatorType === "link" || r.name.endsWith(".css")
    );
    const imageResources = resources.filter(
      (r) => r.initiatorType === "img" || /\.(jpg|jpeg|png|gif|webp|svg)/.test(r.name)
    );

    return {
      totalResources: resources.length,
      totalTransferSize: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0),
      jsResources: jsResources.length,
      jsTransferSize: jsResources.reduce((sum, r) => sum + (r.transferSize || 0), 0),
      cssResources: cssResources.length,
      cssTransferSize: cssResources.reduce((sum, r) => sum + (r.transferSize || 0), 0),
      imageResources: imageResources.length,
      imageTransferSize: imageResources.reduce((sum, r) => sum + (r.transferSize || 0), 0),
    };
  });

  return {
    ...navigationTiming,
    ...paintTiming,
    largestContentfulPaint: lcp as number | null,
    ...resourceTiming,
  };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatMs(ms: number | null): string {
  if (ms === null) return "N/A";
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

test.describe("Performance Tests", () => {
  test("Home page performance", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });
    await page.waitForTimeout(1000); // Allow time for LCP

    const metrics = await measurePerformance(page);

    console.log("\n📊 HOME PAGE PERFORMANCE METRICS");
    console.log("================================");
    console.log("\n⏱️  Timing:");
    console.log(`   DOM Content Loaded: ${formatMs(metrics.domContentLoaded)}`);
    console.log(`   DOM Complete:       ${formatMs(metrics.domComplete)}`);
    console.log(`   Load Complete:      ${formatMs(metrics.loadComplete)}`);
    console.log("\n🎨 Paint Metrics:");
    console.log(`   First Paint (FP):              ${formatMs(metrics.firstPaint)}`);
    console.log(`   First Contentful Paint (FCP):  ${formatMs(metrics.firstContentfulPaint)}`);
    console.log(`   Largest Contentful Paint (LCP): ${formatMs(metrics.largestContentfulPaint)}`);
    console.log("\n📦 Resources:");
    console.log(
      `   Total: ${metrics.totalResources} resources (${formatBytes(metrics.totalTransferSize)})`
    );
    console.log(`   JS:    ${metrics.jsResources} files (${formatBytes(metrics.jsTransferSize)})`);
    console.log(
      `   CSS:   ${metrics.cssResources} files (${formatBytes(metrics.cssTransferSize)})`
    );
    console.log(
      `   Images: ${metrics.imageResources} files (${formatBytes(metrics.imageTransferSize)})`
    );

    // Assertions for performance budgets
    expect(metrics.firstContentfulPaint).toBeLessThan(FCP_BUDGET);
    expect(metrics.domContentLoaded).toBeLessThan(DCL_BUDGET);
  });

  test("Books page performance", async ({ page }) => {
    await page.goto("/books", { waitUntil: "networkidle" });
    await page.waitForTimeout(2000); // Allow time for images and LCP

    const metrics = await measurePerformance(page);

    console.log("\n📊 BOOKS PAGE PERFORMANCE METRICS");
    console.log("=================================");
    console.log("\n⏱️  Timing:");
    console.log(`   DOM Content Loaded: ${formatMs(metrics.domContentLoaded)}`);
    console.log(`   DOM Complete:       ${formatMs(metrics.domComplete)}`);
    console.log(`   Load Complete:      ${formatMs(metrics.loadComplete)}`);
    console.log("\n🎨 Paint Metrics:");
    console.log(`   First Paint (FP):              ${formatMs(metrics.firstPaint)}`);
    console.log(`   First Contentful Paint (FCP):  ${formatMs(metrics.firstContentfulPaint)}`);
    console.log(`   Largest Contentful Paint (LCP): ${formatMs(metrics.largestContentfulPaint)}`);
    console.log("\n📦 Resources:");
    console.log(
      `   Total: ${metrics.totalResources} resources (${formatBytes(metrics.totalTransferSize)})`
    );
    console.log(`   JS:    ${metrics.jsResources} files (${formatBytes(metrics.jsTransferSize)})`);
    console.log(
      `   CSS:   ${metrics.cssResources} files (${formatBytes(metrics.cssTransferSize)})`
    );
    console.log(
      `   Images: ${metrics.imageResources} files (${formatBytes(metrics.imageTransferSize)})`
    );

    // Books page may be slower due to images
    expect(metrics.firstContentfulPaint).toBeLessThan(BOOKS_FCP_BUDGET);
  });

  test("Book detail page performance", async ({ page }) => {
    await page.goto("/books/401", { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);

    const metrics = await measurePerformance(page);

    console.log("\n📊 BOOK DETAIL PAGE PERFORMANCE METRICS");
    console.log("=======================================");
    console.log("\n⏱️  Timing:");
    console.log(`   DOM Content Loaded: ${formatMs(metrics.domContentLoaded)}`);
    console.log(`   DOM Complete:       ${formatMs(metrics.domComplete)}`);
    console.log(`   Load Complete:      ${formatMs(metrics.loadComplete)}`);
    console.log("\n🎨 Paint Metrics:");
    console.log(`   First Paint (FP):              ${formatMs(metrics.firstPaint)}`);
    console.log(`   First Contentful Paint (FCP):  ${formatMs(metrics.firstContentfulPaint)}`);
    console.log(`   Largest Contentful Paint (LCP): ${formatMs(metrics.largestContentfulPaint)}`);
    console.log("\n📦 Resources:");
    console.log(
      `   Total: ${metrics.totalResources} resources (${formatBytes(metrics.totalTransferSize)})`
    );
    console.log(`   JS:    ${metrics.jsResources} files (${formatBytes(metrics.jsTransferSize)})`);
    console.log(
      `   CSS:   ${metrics.cssResources} files (${formatBytes(metrics.cssTransferSize)})`
    );
    console.log(
      `   Images: ${metrics.imageResources} files (${formatBytes(metrics.imageTransferSize)})`
    );

    expect(metrics.firstContentfulPaint).toBeLessThan(BOOKS_FCP_BUDGET);
  });

  test("Core Web Vitals summary", async ({ page }) => {
    const pages = [
      { name: "Home", url: "/" },
      { name: "Books", url: "/books" },
      { name: "Book Detail", url: "/books/401" },
    ];

    console.log("\n╔══════════════════════════════════════════════════════════════════╗");
    console.log("║              CORE WEB VITALS SUMMARY                             ║");
    console.log("╠══════════════════════════════════════════════════════════════════╣");
    console.log("║  Page         │  FCP      │  LCP      │  DCL      │  Transfer   ║");
    console.log("╠═══════════════╪═══════════╪═══════════╪═══════════╪═════════════╣");

    for (const p of pages) {
      await page.goto(p.url, { waitUntil: "networkidle" });
      await page.waitForTimeout(1500);
      const metrics = await measurePerformance(page);

      const fcp = metrics.firstContentfulPaint
        ? `${metrics.firstContentfulPaint.toFixed(0)}ms`.padEnd(9)
        : "N/A".padEnd(9);
      const lcp = metrics.largestContentfulPaint
        ? `${metrics.largestContentfulPaint.toFixed(0)}ms`.padEnd(9)
        : "N/A".padEnd(9);
      const dcl = `${metrics.domContentLoaded.toFixed(0)}ms`.padEnd(9);
      const transfer = formatBytes(metrics.totalTransferSize).padEnd(11);

      console.log(`║  ${p.name.padEnd(12)} │  ${fcp} │  ${lcp} │  ${dcl} │  ${transfer} ║`);
    }

    console.log("╚══════════════════════════════════════════════════════════════════╝");
    console.log("\n📋 Web Vitals Targets (Google):");
    console.log("   FCP: Good < 1.8s, Needs Improvement < 3s, Poor > 3s");
    console.log("   LCP: Good < 2.5s, Needs Improvement < 4s, Poor > 4s");
  });
});
