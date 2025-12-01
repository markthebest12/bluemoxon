import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useBooksStore } from "../books";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/services/api";

describe("Books Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("has empty books array", () => {
      const store = useBooksStore();
      expect(store.books).toEqual([]);
    });

    it("has null currentBook", () => {
      const store = useBooksStore();
      expect(store.currentBook).toBeNull();
    });

    it("has loading false", () => {
      const store = useBooksStore();
      expect(store.loading).toBe(false);
    });

    it("has null error", () => {
      const store = useBooksStore();
      expect(store.error).toBeNull();
    });

    it("has default pagination", () => {
      const store = useBooksStore();
      expect(store.page).toBe(1);
      expect(store.perPage).toBe(20);
      expect(store.total).toBe(0);
    });

    it("has default sorting", () => {
      const store = useBooksStore();
      expect(store.sortBy).toBe("title");
      expect(store.sortOrder).toBe("asc");
    });
  });

  describe("fetchBooks", () => {
    it("sets loading state during fetch", async () => {
      const store = useBooksStore();
      const mockResponse = { data: { items: [], total: 0 } };
      vi.mocked(api.get).mockResolvedValue(mockResponse);

      const promise = store.fetchBooks();
      expect(store.loading).toBe(true);

      await promise;
      expect(store.loading).toBe(false);
    });

    it("updates books and total on success", async () => {
      const store = useBooksStore();
      const mockBooks = [{ id: 1, title: "Test Book", author: null, publisher: null }];
      vi.mocked(api.get).mockResolvedValue({
        data: { items: mockBooks, total: 1 },
      });

      await store.fetchBooks();

      expect(store.books).toEqual(mockBooks);
      expect(store.total).toBe(1);
      expect(store.error).toBeNull();
    });

    it("sets error on failure", async () => {
      const store = useBooksStore();
      vi.mocked(api.get).mockRejectedValue(new Error("Network error"));

      await store.fetchBooks();

      expect(store.books).toEqual([]);
      expect(store.error).toBe("Network error");
    });

    it("includes pagination and sort params", async () => {
      const store = useBooksStore();
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } });

      await store.fetchBooks();

      expect(api.get).toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({
          page: 1,
          per_page: 20,
          sort_by: "title",
          sort_order: "asc",
        }),
      });
    });
  });

  describe("fetchBook", () => {
    it("fetches single book by id", async () => {
      const store = useBooksStore();
      const mockBook = { id: 42, title: "Single Book" };
      vi.mocked(api.get).mockResolvedValue({ data: mockBook });

      await store.fetchBook(42);

      expect(api.get).toHaveBeenCalledWith("/books/42");
      expect(store.currentBook).toEqual(mockBook);
    });

    it("sets error on failure", async () => {
      const store = useBooksStore();
      vi.mocked(api.get).mockRejectedValue(new Error("Not found"));

      await store.fetchBook(999);

      expect(store.error).toBe("Not found");
    });
  });

  describe("createBook", () => {
    it("posts book data and returns result", async () => {
      const store = useBooksStore();
      const newBook = { title: "New Book", volumes: 1 };
      const createdBook = { id: 100, ...newBook };
      vi.mocked(api.post).mockResolvedValue({ data: createdBook });

      const result = await store.createBook(newBook);

      expect(api.post).toHaveBeenCalledWith("/books", newBook);
      expect(result).toEqual(createdBook);
    });

    it("throws and sets error on failure", async () => {
      const store = useBooksStore();
      vi.mocked(api.post).mockRejectedValue(new Error("Validation failed"));

      await expect(store.createBook({})).rejects.toThrow();
      expect(store.error).toBe("Validation failed");
    });
  });

  describe("updateBook", () => {
    it("updates book and sets currentBook", async () => {
      const store = useBooksStore();
      const updates = { title: "Updated Title" };
      const updatedBook = { id: 1, title: "Updated Title" };
      vi.mocked(api.put).mockResolvedValue({ data: updatedBook });

      const result = await store.updateBook(1, updates);

      expect(api.put).toHaveBeenCalledWith("/books/1", updates);
      expect(store.currentBook).toEqual(updatedBook);
      expect(result).toEqual(updatedBook);
    });
  });

  describe("deleteBook", () => {
    it("deletes book by id", async () => {
      const store = useBooksStore();
      vi.mocked(api.delete).mockResolvedValue({});

      await store.deleteBook(1);

      expect(api.delete).toHaveBeenCalledWith("/books/1");
    });
  });

  describe("setFilters", () => {
    it("updates filters and resets page", async () => {
      const store = useBooksStore();
      store.page = 5;
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } });

      store.setFilters({ status: "ON_HAND" });

      expect(store.filters).toEqual({ status: "ON_HAND" });
      expect(store.page).toBe(1);
    });
  });

  describe("setSort", () => {
    it("updates sort field and order", async () => {
      const store = useBooksStore();
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } });

      store.setSort("value_mid", "desc");

      expect(store.sortBy).toBe("value_mid");
      expect(store.sortOrder).toBe("desc");
    });
  });

  describe("setPage", () => {
    it("updates page number", async () => {
      const store = useBooksStore();
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } });

      store.setPage(3);

      expect(store.page).toBe(3);
    });
  });

  describe("totalPages computed", () => {
    it("calculates pages from total and perPage", () => {
      const store = useBooksStore();
      store.total = 45;
      store.perPage = 20;

      expect(store.totalPages).toBe(3);
    });

    it("returns 0 for empty results", () => {
      const store = useBooksStore();
      expect(store.totalPages).toBe(0);
    });
  });
});
