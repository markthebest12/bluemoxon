import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useReferencesStore } from "../references";
import { api } from "@/services/api";

vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("references store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("createAuthor", () => {
    it("creates author and adds to list", async () => {
      const store = useReferencesStore();
      const mockAuthor = { id: 100, name: "New Author" };
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockAuthor });

      const result = await store.createAuthor("New Author");

      expect(api.post).toHaveBeenCalledWith("/authors", { name: "New Author" });
      expect(result).toEqual(mockAuthor);
      expect(store.authors).toContainEqual(mockAuthor);
    });
  });

  describe("createPublisher", () => {
    it("creates publisher and adds to list", async () => {
      const store = useReferencesStore();
      const mockPublisher = { id: 100, name: "New Publisher", tier: null, book_count: 0 };
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockPublisher });

      const result = await store.createPublisher("New Publisher");

      expect(api.post).toHaveBeenCalledWith("/publishers", { name: "New Publisher" });
      expect(result).toEqual(mockPublisher);
      expect(store.publishers).toContainEqual(mockPublisher);
    });
  });

  describe("createBinder", () => {
    it("creates binder and adds to list", async () => {
      const store = useReferencesStore();
      const mockBinder = { id: 100, name: "New Binder", full_name: null, authentication_markers: null, book_count: 0 };
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockBinder });

      const result = await store.createBinder("New Binder");

      expect(api.post).toHaveBeenCalledWith("/binders", { name: "New Binder" });
      expect(result).toEqual(mockBinder);
      expect(store.binders).toContainEqual(mockBinder);
    });
  });
});
