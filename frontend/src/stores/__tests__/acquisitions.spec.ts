import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAcquisitionsStore } from "../acquisitions";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/services/api";

describe("Acquisitions Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("has empty arrays for all columns", () => {
      const store = useAcquisitionsStore();
      expect(store.evaluating).toEqual([]);
      expect(store.inTransit).toEqual([]);
      expect(store.received).toEqual([]);
    });

    it("has loading false", () => {
      const store = useAcquisitionsStore();
      expect(store.loading).toBe(false);
    });

    it("has null error", () => {
      const store = useAcquisitionsStore();
      expect(store.error).toBeNull();
    });

    it("has zero counts initially", () => {
      const store = useAcquisitionsStore();
      expect(store.evaluatingCount).toBe(0);
      expect(store.inTransitCount).toBe(0);
      expect(store.receivedCount).toBe(0);
    });
  });

  describe("fetchAll", () => {
    it("fetches books for all three columns", async () => {
      const store = useAcquisitionsStore();

      const mockEvaluating = [{ id: 1, title: "Book 1", status: "EVALUATING" }];
      const mockInTransit = [{ id: 2, title: "Book 2", status: "IN_TRANSIT" }];
      const mockReceived = [
        {
          id: 3,
          title: "Book 3",
          status: "ON_HAND",
          purchase_date: new Date().toISOString(),
        },
      ];

      vi.mocked(api.get)
        .mockResolvedValueOnce({ data: { items: mockEvaluating } })
        .mockResolvedValueOnce({ data: { items: mockInTransit } })
        .mockResolvedValueOnce({ data: { items: mockReceived } });

      await store.fetchAll();

      expect(store.evaluating).toHaveLength(1);
      expect(store.evaluating[0].title).toBe("Book 1");
      expect(store.inTransit).toHaveLength(1);
      expect(store.inTransit[0].title).toBe("Book 2");
      expect(store.received).toHaveLength(1);
      expect(store.received[0].title).toBe("Book 3");
      expect(store.loading).toBe(false);
      expect(store.error).toBeNull();
    });

    it("sets error on failure", async () => {
      const store = useAcquisitionsStore();
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      await store.fetchAll();

      expect(store.error).toBe("Network error");
      expect(store.evaluating).toEqual([]);
      expect(store.inTransit).toEqual([]);
      expect(store.received).toEqual([]);
    });

    it("filters out received items older than 30 days", async () => {
      const store = useAcquisitionsStore();

      const today = new Date();
      const twentyDaysAgo = new Date();
      twentyDaysAgo.setDate(today.getDate() - 20);
      const fortyDaysAgo = new Date();
      fortyDaysAgo.setDate(today.getDate() - 40);

      const mockReceived = [
        { id: 1, title: "Recent", purchase_date: twentyDaysAgo.toISOString() },
        { id: 2, title: "Old", purchase_date: fortyDaysAgo.toISOString() },
      ];

      vi.mocked(api.get)
        .mockResolvedValueOnce({ data: { items: [] } })
        .mockResolvedValueOnce({ data: { items: [] } })
        .mockResolvedValueOnce({ data: { items: mockReceived } });

      await store.fetchAll();

      expect(store.received).toHaveLength(1);
      expect(store.received[0].title).toBe("Recent");
    });

    it("sets loading state during fetch", async () => {
      const store = useAcquisitionsStore();
      vi.mocked(api.get).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: { items: [] } }), 100))
      );

      const promise = store.fetchAll();
      expect(store.loading).toBe(true);

      await promise;
      expect(store.loading).toBe(false);
    });
  });

  describe("acquireBook", () => {
    it("moves book from evaluating to inTransit", async () => {
      const store = useAcquisitionsStore();
      store.evaluating = [
        { id: 1, title: "Test Book", status: "EVALUATING" } as any,
        { id: 2, title: "Other Book", status: "EVALUATING" } as any,
      ];

      const acquiredBook = {
        id: 1,
        title: "Test Book",
        status: "IN_TRANSIT",
        purchase_price: 164.14,
      };

      vi.mocked(api.patch).mockResolvedValueOnce({ data: acquiredBook });

      const payload = {
        purchase_price: 164.14,
        purchase_date: "2025-12-10",
        order_number: "19-13940-40744",
        place_of_purchase: "eBay",
      };

      await store.acquireBook(1, payload);

      expect(api.patch).toHaveBeenCalledWith("/books/1/acquire", payload);
      expect(store.evaluating).toHaveLength(1);
      expect(store.evaluating[0].id).toBe(2);
      expect(store.inTransit).toHaveLength(1);
      expect(store.inTransit[0].id).toBe(1);
      expect(store.inTransit[0].status).toBe("IN_TRANSIT");
      expect(store.inTransit[0].purchase_price).toBe(164.14);
    });

    it("prepends acquired book to inTransit array", async () => {
      const store = useAcquisitionsStore();
      store.evaluating = [{ id: 1, title: "New Book", status: "EVALUATING" } as any];
      store.inTransit = [{ id: 2, title: "Old Book", status: "IN_TRANSIT" } as any];

      const acquiredBook = { id: 1, title: "New Book", status: "IN_TRANSIT" };
      vi.mocked(api.patch).mockResolvedValueOnce({ data: acquiredBook });

      await store.acquireBook(1, {
        purchase_price: 100,
        purchase_date: "2025-12-10",
        order_number: "123",
        place_of_purchase: "eBay",
      });

      expect(store.inTransit[0].id).toBe(1); // New book at top
      expect(store.inTransit[1].id).toBe(2);
    });
  });

  describe("markReceived", () => {
    it("moves book from inTransit to received", async () => {
      const store = useAcquisitionsStore();
      store.inTransit = [
        { id: 1, title: "Test Book", status: "IN_TRANSIT" } as any,
        { id: 2, title: "Other Book", status: "IN_TRANSIT" } as any,
      ];

      const receivedBook = { id: 1, title: "Test Book", status: "ON_HAND" };
      vi.mocked(api.patch).mockResolvedValueOnce({ data: receivedBook });

      await store.markReceived(1);

      expect(api.patch).toHaveBeenCalledWith("/books/1/status", null, {
        params: { status: "ON_HAND" },
      });
      expect(store.inTransit).toHaveLength(1);
      expect(store.inTransit[0].id).toBe(2);
      expect(store.received).toHaveLength(1);
      expect(store.received[0].id).toBe(1);
      expect(store.received[0].status).toBe("ON_HAND");
    });

    it("prepends received book to received array", async () => {
      const store = useAcquisitionsStore();
      store.inTransit = [{ id: 1, title: "New Book", status: "IN_TRANSIT" } as any];
      store.received = [{ id: 2, title: "Old Book", status: "ON_HAND" } as any];

      const receivedBook = { id: 1, title: "New Book", status: "ON_HAND" };
      vi.mocked(api.patch).mockResolvedValueOnce({ data: receivedBook });

      await store.markReceived(1);

      expect(store.received[0].id).toBe(1); // New book at top
      expect(store.received[1].id).toBe(2);
    });
  });

  describe("cancelOrder", () => {
    it("removes book from inTransit and sets status to CANCELED", async () => {
      const store = useAcquisitionsStore();
      store.inTransit = [
        { id: 1, title: "Test Book", status: "IN_TRANSIT" } as any,
        { id: 2, title: "Other Book", status: "IN_TRANSIT" } as any,
      ];

      const canceledBook = { id: 1, title: "Test Book", status: "CANCELED" };
      vi.mocked(api.patch).mockResolvedValueOnce({ data: canceledBook });

      await store.cancelOrder(1);

      expect(api.patch).toHaveBeenCalledWith("/books/1/status", null, {
        params: { status: "CANCELED" },
      });
      expect(store.inTransit).toHaveLength(1);
      expect(store.inTransit[0].id).toBe(2);
    });
  });

  describe("deleteEvaluating", () => {
    it("removes book from evaluating array", async () => {
      const store = useAcquisitionsStore();
      store.evaluating = [
        { id: 1, title: "Test Book", status: "EVALUATING" } as any,
        { id: 2, title: "Other Book", status: "EVALUATING" } as any,
      ];

      vi.mocked(api.delete).mockResolvedValueOnce({});

      await store.deleteEvaluating(1);

      expect(api.delete).toHaveBeenCalledWith("/books/1");
      expect(store.evaluating).toHaveLength(1);
      expect(store.evaluating[0].id).toBe(2);
    });
  });

  describe("computed properties", () => {
    it("evaluatingCount returns length of evaluating array", () => {
      const store = useAcquisitionsStore();
      store.evaluating = [{ id: 1, title: "Book 1" } as any, { id: 2, title: "Book 2" } as any];

      expect(store.evaluatingCount).toBe(2);
    });

    it("inTransitCount returns length of inTransit array", () => {
      const store = useAcquisitionsStore();
      store.inTransit = [{ id: 1, title: "Book 1" } as any];

      expect(store.inTransitCount).toBe(1);
    });

    it("receivedCount returns length of received array", () => {
      const store = useAcquisitionsStore();
      store.received = [
        { id: 1, title: "Book 1" } as any,
        { id: 2, title: "Book 2" } as any,
        { id: 3, title: "Book 3" } as any,
      ];

      expect(store.receivedCount).toBe(3);
    });
  });
});
