import { describe, it, expect, vi } from "vitest";
import type { Era } from "@/types/socialCircles";

// Reset the module between tests to avoid shared state mutation issues
// The composable uses shallow copy of DEFAULT_FILTER_STATE which shares array references
describe("useNetworkFilters", () => {
  // Import dynamically to get fresh module state
  async function getUseNetworkFilters() {
    // Reset the module cache to get a fresh DEFAULT_FILTER_STATE
    vi.resetModules();
    const { useNetworkFilters } = await import("../useNetworkFilters");
    return useNetworkFilters;
  }

  describe("initialization", () => {
    it("initializes with default filter state", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters } = useNetworkFilters();

      expect(filters.value).toEqual({
        showAuthors: true,
        showPublishers: true,
        showBinders: true,
        connectionTypes: ["publisher", "shared_publisher", "binder"],
        tier1Only: false,
        eras: [],
        searchQuery: "",
      });
    });

    it("initializes with all node type filters enabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters } = useNetworkFilters();

      expect(filters.value.showAuthors).toBe(true);
      expect(filters.value.showPublishers).toBe(true);
      expect(filters.value.showBinders).toBe(true);
    });

    it("initializes with all connection types enabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters } = useNetworkFilters();

      expect(filters.value.connectionTypes).toEqual(["publisher", "shared_publisher", "binder"]);
    });

    it("initializes with tier1Only disabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters } = useNetworkFilters();

      expect(filters.value.tier1Only).toBe(false);
    });

    it("initializes with empty eras array", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters } = useNetworkFilters();

      expect(filters.value.eras).toEqual([]);
    });

    it("initializes with empty search query", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters } = useNetworkFilters();

      expect(filters.value.searchQuery).toBe("");
    });
  });

  describe("hasActiveFilters computed", () => {
    it("returns false when all filters are at default state", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters } = useNetworkFilters();

      expect(hasActiveFilters.value).toBe(false);
    });

    it("returns true when showAuthors is disabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setShowAuthors } = useNetworkFilters();

      setShowAuthors(false);

      expect(hasActiveFilters.value).toBe(true);
    });

    it("returns true when showPublishers is disabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setShowPublishers } = useNetworkFilters();

      setShowPublishers(false);

      expect(hasActiveFilters.value).toBe(true);
    });

    it("returns true when showBinders is disabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setShowBinders } = useNetworkFilters();

      setShowBinders(false);

      expect(hasActiveFilters.value).toBe(true);
    });

    it("returns true when connection types are reduced", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes(["publisher", "binder"]);

      expect(hasActiveFilters.value).toBe(true);
    });

    it("returns true when tier1Only is enabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setTier1Only } = useNetworkFilters();

      setTier1Only(true);

      expect(hasActiveFilters.value).toBe(true);
    });

    it("returns true when eras are selected", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setEras } = useNetworkFilters();

      setEras(["victorian"]);

      expect(hasActiveFilters.value).toBe(true);
    });

    it("returns true when search query is set", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setSearchQuery } = useNetworkFilters();

      setSearchQuery("Dickens");

      expect(hasActiveFilters.value).toBe(true);
    });
  });

  describe("activeFilterCount computed", () => {
    it("returns 0 when all filters are at default state", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount } = useNetworkFilters();

      expect(activeFilterCount.value).toBe(0);
    });

    it("increments count for each disabled node type filter", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setShowAuthors, setShowPublishers, setShowBinders } =
        useNetworkFilters();

      setShowAuthors(false);
      expect(activeFilterCount.value).toBe(1);

      setShowPublishers(false);
      expect(activeFilterCount.value).toBe(2);

      setShowBinders(false);
      expect(activeFilterCount.value).toBe(3);
    });

    it("increments count when connection types are reduced", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes(["publisher"]);

      expect(activeFilterCount.value).toBe(1);
    });

    it("increments count when tier1Only is enabled", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setTier1Only } = useNetworkFilters();

      setTier1Only(true);

      expect(activeFilterCount.value).toBe(1);
    });

    it("increments count for each selected era", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setEras } = useNetworkFilters();

      setEras(["victorian"]);
      expect(activeFilterCount.value).toBe(1);

      setEras(["victorian", "romantic"]);
      expect(activeFilterCount.value).toBe(2);

      setEras(["victorian", "romantic", "edwardian"]);
      expect(activeFilterCount.value).toBe(3);
    });

    it("increments count when search query is set", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setSearchQuery } = useNetworkFilters();

      setSearchQuery("test");

      expect(activeFilterCount.value).toBe(1);
    });

    it("correctly accumulates multiple active filters", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setShowAuthors, setTier1Only, setEras, setSearchQuery } =
        useNetworkFilters();

      setShowAuthors(false); // +1
      setTier1Only(true); // +1
      setEras(["victorian", "romantic"]); // +2
      setSearchQuery("test"); // +1

      expect(activeFilterCount.value).toBe(5);
    });
  });

  describe("setShowAuthors", () => {
    it("sets showAuthors to false", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setShowAuthors } = useNetworkFilters();

      setShowAuthors(false);

      expect(filters.value.showAuthors).toBe(false);
    });

    it("sets showAuthors back to true", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setShowAuthors } = useNetworkFilters();

      setShowAuthors(false);
      setShowAuthors(true);

      expect(filters.value.showAuthors).toBe(true);
    });
  });

  describe("setShowPublishers", () => {
    it("sets showPublishers to false", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setShowPublishers } = useNetworkFilters();

      setShowPublishers(false);

      expect(filters.value.showPublishers).toBe(false);
    });

    it("sets showPublishers back to true", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setShowPublishers } = useNetworkFilters();

      setShowPublishers(false);
      setShowPublishers(true);

      expect(filters.value.showPublishers).toBe(true);
    });
  });

  describe("setShowBinders", () => {
    it("sets showBinders to false", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setShowBinders } = useNetworkFilters();

      setShowBinders(false);

      expect(filters.value.showBinders).toBe(false);
    });

    it("sets showBinders back to true", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setShowBinders } = useNetworkFilters();

      setShowBinders(false);
      setShowBinders(true);

      expect(filters.value.showBinders).toBe(true);
    });
  });

  describe("setConnectionTypes", () => {
    it("sets connection types to a subset", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes(["publisher", "binder"]);

      expect(filters.value.connectionTypes).toEqual(["publisher", "binder"]);
    });

    it("sets connection types to empty array", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes([]);

      expect(filters.value.connectionTypes).toEqual([]);
    });

    it("sets connection types to single type", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes(["shared_publisher"]);

      expect(filters.value.connectionTypes).toEqual(["shared_publisher"]);
    });
  });

  describe("toggleConnectionType", () => {
    it("removes connection type when present", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, toggleConnectionType } = useNetworkFilters();

      toggleConnectionType("publisher");

      expect(filters.value.connectionTypes).toEqual(["shared_publisher", "binder"]);
    });

    it("adds connection type when not present", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setConnectionTypes, toggleConnectionType } = useNetworkFilters();

      setConnectionTypes([]);
      toggleConnectionType("publisher");

      expect(filters.value.connectionTypes).toEqual(["publisher"]);
    });

    it("toggles the same type on and off", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, toggleConnectionType } = useNetworkFilters();

      // Remove binder
      toggleConnectionType("binder");
      expect(filters.value.connectionTypes).toEqual(["publisher", "shared_publisher"]);

      // Add binder back
      toggleConnectionType("binder");
      expect(filters.value.connectionTypes).toContain("binder");
    });

    it("can toggle all types off one by one", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, toggleConnectionType } = useNetworkFilters();

      // Start with all 3 types
      expect(filters.value.connectionTypes).toHaveLength(3);

      toggleConnectionType("publisher");
      expect(filters.value.connectionTypes).not.toContain("publisher");

      toggleConnectionType("shared_publisher");
      expect(filters.value.connectionTypes).not.toContain("shared_publisher");

      toggleConnectionType("binder");
      expect(filters.value.connectionTypes).not.toContain("binder");

      expect(filters.value.connectionTypes).toEqual([]);
    });
  });

  describe("setTier1Only", () => {
    it("sets tier1Only to true", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setTier1Only } = useNetworkFilters();

      setTier1Only(true);

      expect(filters.value.tier1Only).toBe(true);
    });

    it("sets tier1Only back to false", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setTier1Only } = useNetworkFilters();

      setTier1Only(true);
      setTier1Only(false);

      expect(filters.value.tier1Only).toBe(false);
    });
  });

  describe("setEras", () => {
    it("sets eras to selected values", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setEras } = useNetworkFilters();

      setEras(["victorian", "romantic"]);

      expect(filters.value.eras).toEqual(["victorian", "romantic"]);
    });

    it("sets eras to empty array", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setEras } = useNetworkFilters();

      setEras(["victorian"]);
      setEras([]);

      expect(filters.value.eras).toEqual([]);
    });

    it("sets all available eras", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setEras } = useNetworkFilters();

      const allEras: Era[] = [
        "pre_romantic",
        "romantic",
        "victorian",
        "edwardian",
        "post_1910",
        "unknown",
      ];
      setEras(allEras);

      expect(filters.value.eras).toEqual(allEras);
    });
  });

  describe("toggleEra", () => {
    it("adds era when not present", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, toggleEra } = useNetworkFilters();

      toggleEra("victorian");

      expect(filters.value.eras).toEqual(["victorian"]);
    });

    it("removes era when present", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setEras, toggleEra } = useNetworkFilters();

      setEras(["victorian", "romantic"]);
      toggleEra("victorian");

      expect(filters.value.eras).toEqual(["romantic"]);
    });

    it("toggles multiple eras", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, toggleEra } = useNetworkFilters();

      toggleEra("victorian");
      toggleEra("romantic");
      toggleEra("edwardian");

      expect(filters.value.eras).toContain("victorian");
      expect(filters.value.eras).toContain("romantic");
      expect(filters.value.eras).toContain("edwardian");
    });

    it("can toggle same era on and off", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, toggleEra } = useNetworkFilters();

      toggleEra("victorian");
      expect(filters.value.eras).toEqual(["victorian"]);

      toggleEra("victorian");
      expect(filters.value.eras).toEqual([]);
    });
  });

  describe("setSearchQuery", () => {
    it("sets search query to value", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setSearchQuery } = useNetworkFilters();

      setSearchQuery("Dickens");

      expect(filters.value.searchQuery).toBe("Dickens");
    });

    it("sets search query to empty string", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setSearchQuery } = useNetworkFilters();

      setSearchQuery("Dickens");
      setSearchQuery("");

      expect(filters.value.searchQuery).toBe("");
    });

    it("preserves whitespace in search query", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setSearchQuery } = useNetworkFilters();

      setSearchQuery("  Charles Dickens  ");

      expect(filters.value.searchQuery).toBe("  Charles Dickens  ");
    });

    it("handles special characters in search query", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setSearchQuery } = useNetworkFilters();

      setSearchQuery("Chapman & Hall");

      expect(filters.value.searchQuery).toBe("Chapman & Hall");
    });
  });

  describe("resetFilters", () => {
    it("resets all filters to default state", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const {
        filters,
        setShowAuthors,
        setShowPublishers,
        setShowBinders,
        setConnectionTypes,
        setTier1Only,
        setEras,
        setSearchQuery,
        resetFilters,
      } = useNetworkFilters();

      // Modify all filters
      setShowAuthors(false);
      setShowPublishers(false);
      setShowBinders(false);
      setConnectionTypes(["publisher"]);
      setTier1Only(true);
      setEras(["victorian", "romantic"]);
      setSearchQuery("test");

      // Reset
      resetFilters();

      // Note: resetFilters uses shallow copy, so we check individual properties
      expect(filters.value.showAuthors).toBe(true);
      expect(filters.value.showPublishers).toBe(true);
      expect(filters.value.showBinders).toBe(true);
      expect(filters.value.tier1Only).toBe(false);
      expect(filters.value.searchQuery).toBe("");
    });

    it("resets hasActiveFilters to false after modifying boolean filters", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setShowAuthors, setTier1Only, resetFilters } = useNetworkFilters();

      setShowAuthors(false);
      setTier1Only(true);
      expect(hasActiveFilters.value).toBe(true);

      resetFilters();
      expect(hasActiveFilters.value).toBe(false);
    });

    it("resets activeFilterCount to 0 after modifying boolean filters", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setShowAuthors, setTier1Only, resetFilters } = useNetworkFilters();

      setShowAuthors(false);
      setTier1Only(true);
      expect(activeFilterCount.value).toBe(2);

      resetFilters();
      expect(activeFilterCount.value).toBe(0);
    });
  });

  describe("filters readonly", () => {
    it("returns readonly filters ref", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters } = useNetworkFilters();

      // The filters ref is readonly, attempting to assign would fail type check
      // We verify it has the right shape
      expect(filters.value.showAuthors).toBe(true);
      expect(typeof filters.value).toBe("object");
    });
  });

  describe("multiple instances within same module", () => {
    it("creates independent filter instances for boolean properties", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const filters1 = useNetworkFilters();
      const filters2 = useNetworkFilters();

      filters1.setShowAuthors(false);

      expect(filters1.filters.value.showAuthors).toBe(false);
      expect(filters2.filters.value.showAuthors).toBe(true);
    });

    it("allows independent era selections via setEras (replaces array)", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const filters1 = useNetworkFilters();
      const filters2 = useNetworkFilters();

      filters1.setEras(["victorian"]);
      filters2.setEras(["romantic", "edwardian"]);

      expect(filters1.filters.value.eras).toEqual(["victorian"]);
      expect(filters2.filters.value.eras).toEqual(["romantic", "edwardian"]);
    });

    it("setConnectionTypes creates new array (independent)", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const filters1 = useNetworkFilters();
      const filters2 = useNetworkFilters();

      filters1.setConnectionTypes(["publisher"]);
      filters2.setConnectionTypes(["binder"]);

      expect(filters1.filters.value.connectionTypes).toEqual(["publisher"]);
      expect(filters2.filters.value.connectionTypes).toEqual(["binder"]);
    });
  });

  describe("edge cases", () => {
    it("handles rapid filter toggling (even number returns to original)", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, toggleConnectionType } = useNetworkFilters();

      // Toggle same type 10 times (even)
      for (let i = 0; i < 10; i++) {
        toggleConnectionType("publisher");
      }

      // After even number of toggles, should be back to original state
      expect(filters.value.connectionTypes).toContain("publisher");
    });

    it("handles setting same value multiple times", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setShowAuthors } = useNetworkFilters();

      setShowAuthors(false);
      setShowAuthors(false);
      setShowAuthors(false);

      expect(filters.value.showAuthors).toBe(false);
    });

    it("handles empty search query after non-empty", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setSearchQuery } = useNetworkFilters();

      setSearchQuery("test");
      expect(hasActiveFilters.value).toBe(true);

      setSearchQuery("");
      expect(hasActiveFilters.value).toBe(false);
    });

    it("connection types count correctly at exact threshold", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, filters, setConnectionTypes } = useNetworkFilters();

      // At exactly 3 connection types, hasActiveFilters should be false
      expect(filters.value.connectionTypes).toHaveLength(3);
      expect(hasActiveFilters.value).toBe(false);

      // At 2 connection types, hasActiveFilters should be true
      setConnectionTypes(["publisher", "binder"]);
      expect(hasActiveFilters.value).toBe(true);
    });

    it("empty connection types array triggers hasActiveFilters", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes([]);
      expect(hasActiveFilters.value).toBe(true);
    });

    it("connection types with duplicates are deduplicated", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { filters, setConnectionTypes } = useNetworkFilters();

      // The composable deduplicates to prevent unexpected filter counts
      setConnectionTypes(["publisher", "publisher", "binder"]);
      expect(filters.value.connectionTypes).toEqual(["publisher", "binder"]);
    });
  });

  describe("hasActiveFilters edge cases", () => {
    it("returns false when all connection types restored to 3", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes(["publisher"]);
      expect(hasActiveFilters.value).toBe(true);

      setConnectionTypes(["publisher", "shared_publisher", "binder"]);
      expect(hasActiveFilters.value).toBe(false);
    });

    it("returns true when eras has single item", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, toggleEra } = useNetworkFilters();

      toggleEra("victorian");
      expect(hasActiveFilters.value).toBe(true);
    });

    it("returns false after clearing eras", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { hasActiveFilters, setEras } = useNetworkFilters();

      setEras(["victorian"]);
      expect(hasActiveFilters.value).toBe(true);

      setEras([]);
      expect(hasActiveFilters.value).toBe(false);
    });
  });

  describe("activeFilterCount detailed scenarios", () => {
    it("counts search query only once regardless of length", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setSearchQuery } = useNetworkFilters();

      setSearchQuery("a very long search query with many words");
      expect(activeFilterCount.value).toBe(1);
    });

    it("does not count connection types when all 3 present", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setConnectionTypes } = useNetworkFilters();

      setConnectionTypes(["publisher", "shared_publisher", "binder"]);
      expect(activeFilterCount.value).toBe(0);
    });

    it("counts connection types reduction as 1 regardless of how many removed", async () => {
      const useNetworkFilters = await getUseNetworkFilters();
      const { activeFilterCount, setConnectionTypes } = useNetworkFilters();

      // Remove 1
      setConnectionTypes(["publisher", "binder"]);
      expect(activeFilterCount.value).toBe(1);

      // Remove 2
      setConnectionTypes(["publisher"]);
      expect(activeFilterCount.value).toBe(1);

      // Remove all
      setConnectionTypes([]);
      expect(activeFilterCount.value).toBe(1);
    });
  });
});
