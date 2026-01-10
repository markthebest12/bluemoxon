import { describe, it, expect, vi, beforeEach } from "vitest";
import { wantsNewTab, navigateToBooks } from "./chart-navigation";
import type { Router } from "vue-router";

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
});
