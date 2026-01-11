import { describe, it, expect, vi, beforeEach } from "vitest";
import { wantsNewTab, navigateToBooks, normalizeEra } from "./chart-navigation";
import type { Router } from "vue-router";

describe("normalizeEra", () => {
  it("strips parenthetical date range from era", () => {
    expect(normalizeEra("Victorian (1837-1901)")).toBe("Victorian");
  });

  it("handles era with extra whitespace before parenthesis", () => {
    expect(normalizeEra("Edwardian  (1901-1910)")).toBe("Edwardian");
  });

  it("returns era unchanged when no parentheses", () => {
    expect(normalizeEra("Victorian")).toBe("Victorian");
  });

  it("handles empty string", () => {
    expect(normalizeEra("")).toBe("");
  });

  it("preserves non-date parentheses and only strips trailing date range", () => {
    expect(normalizeEra("Georgian (Early) (1714-1760)")).toBe("Georgian (Early)");
  });
});

describe("wantsNewTab", () => {
  it("returns false when event is undefined", () => {
    expect(wantsNewTab(undefined)).toBe(false);
  });

  it("returns false when event is null", () => {
    expect(wantsNewTab(null)).toBe(false);
  });

  it("returns false for normal click (no modifiers)", () => {
    const event = new MouseEvent("click", { ctrlKey: false, metaKey: false });
    expect(wantsNewTab(event)).toBe(false);
  });

  it("returns true when Ctrl is held (Windows/Linux)", () => {
    const event = new MouseEvent("click", { ctrlKey: true, metaKey: false });
    expect(wantsNewTab(event)).toBe(true);
  });

  it("returns true when Meta/Cmd is held (Mac)", () => {
    const event = new MouseEvent("click", { ctrlKey: false, metaKey: true });
    expect(wantsNewTab(event)).toBe(true);
  });

  it("returns true when both Ctrl and Meta are held", () => {
    const event = new MouseEvent("click", { ctrlKey: true, metaKey: true });
    expect(wantsNewTab(event)).toBe(true);
  });
});

describe("navigateToBooks", () => {
  let mockRouter: Router;
  let mockPush: ReturnType<typeof vi.fn>;
  let mockResolve: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockPush = vi.fn().mockResolvedValue(undefined);
    mockResolve = vi.fn().mockReturnValue({ href: "/books?category=Poetry" });
    mockRouter = {
      push: mockPush,
      resolve: mockResolve,
    } as unknown as Router;

    // Reset window.open mock
    vi.stubGlobal("open", vi.fn());
  });

  it("navigates in same tab for normal click", () => {
    const event = new MouseEvent("click", { ctrlKey: false, metaKey: false });
    navigateToBooks(mockRouter, { category: "Poetry" }, event);

    expect(mockPush).toHaveBeenCalledWith({ path: "/books", query: { category: "Poetry" } });
    expect(window.open).not.toHaveBeenCalled();
  });

  it("opens new tab with noopener for Ctrl+Click", () => {
    const mockWindow = { focus: vi.fn() };
    vi.stubGlobal("open", vi.fn().mockReturnValue(mockWindow));

    const event = new MouseEvent("click", { ctrlKey: true, metaKey: false });
    navigateToBooks(mockRouter, { category: "Poetry" }, event);

    expect(mockResolve).toHaveBeenCalledWith({ path: "/books", query: { category: "Poetry" } });
    expect(window.open).toHaveBeenCalledWith("/books?category=Poetry", "_blank", "noopener");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("falls back to same tab when popup is blocked", () => {
    vi.stubGlobal("open", vi.fn().mockReturnValue(null));

    const event = new MouseEvent("click", { ctrlKey: true, metaKey: false });
    navigateToBooks(mockRouter, { category: "Poetry" }, event);

    expect(window.open).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith({ path: "/books", query: { category: "Poetry" } });
  });

  it("navigates in same tab when no event is provided", () => {
    navigateToBooks(mockRouter, { era: "Victorian" });

    expect(mockPush).toHaveBeenCalledWith({ path: "/books", query: { era: "Victorian" } });
    expect(window.open).not.toHaveBeenCalled();
  });

  it("normalizes era filter by stripping parenthetical date range", () => {
    navigateToBooks(mockRouter, { era: "Victorian (1837-1901)" });

    expect(mockPush).toHaveBeenCalledWith({ path: "/books", query: { era: "Victorian" } });
  });

  it("preserves other filters when normalizing era", () => {
    navigateToBooks(mockRouter, { era: "Edwardian (1901-1910)", status: "IN_COLLECTION" });

    expect(mockPush).toHaveBeenCalledWith({
      path: "/books",
      query: { era: "Edwardian", status: "IN_COLLECTION" },
    });
  });
});
