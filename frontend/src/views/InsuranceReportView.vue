<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { api } from "@/services/api";
import type { Book } from "@/stores/books";
import { BOOK_STATUSES, PAGINATION } from "@/constants";

// Report type options
type ReportType = "insurance" | "primary" | "extended" | "all";

const reportType = ref<ReportType>("insurance");
const books = ref<Book[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const reportTypeOptions = [
  {
    value: "insurance",
    label: "Insurance Valuation",
    description: "Primary collection, On-Hand only",
  },
  { value: "primary", label: "Primary Inventory", description: "All Primary collection items" },
  { value: "extended", label: "Extended Inventory", description: "Extended collection only" },
  { value: "all", label: "Full Inventory", description: "All items (Primary + Extended)" },
];

// Fetch books based on report type
async function fetchBooks() {
  loading.value = true;
  error.value = null;

  try {
    const allBooks: Book[] = [];
    let page = 1;
    let hasMore = true;

    // Determine inventory_type filter based on report type
    const inventoryType =
      reportType.value === "extended"
        ? "EXTENDED"
        : reportType.value === "all"
          ? undefined // No filter = all types
          : "PRIMARY"; // insurance and primary both use PRIMARY

    while (hasMore) {
      const params: Record<string, unknown> = {
        page,
        per_page: PAGINATION.DEFAULT_PER_PAGE,
        sort_by: "value_mid",
        sort_order: "desc",
      };
      if (inventoryType) {
        params.inventory_type = inventoryType;
      }

      const response = await api.get("/books", { params });
      allBooks.push(...response.data.items);
      hasMore = page < response.data.pages;
      page++;
    }

    books.value = allBooks;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Failed to fetch books";
  } finally {
    loading.value = false;
  }
}

// Fetch on mount and when report type changes
watch(reportType, () => fetchBooks(), { immediate: true });

// Filter books based on report type
const filteredBooks = computed(() => {
  if (reportType.value === "insurance") {
    // Insurance report: only ON_HAND items
    return books.value.filter((book) => book.status === BOOK_STATUSES.ON_HAND);
  }
  // All other reports: show all fetched items
  return books.value;
});

// Collection statistics
const stats = computed(() => {
  const items = filteredBooks.value;
  const totalItems = items.length;
  const totalVolumes = items.reduce((sum, b) => sum + (b.volumes || 1), 0);
  const totalValueLow = items.reduce((sum, b) => sum + Number(b.value_low || 0), 0);
  const totalValueMid = items.reduce((sum, b) => sum + Number(b.value_mid || 0), 0);
  const totalValueHigh = items.reduce((sum, b) => sum + Number(b.value_high || 0), 0);
  const totalPurchaseCost = items.reduce((sum, b) => sum + Number(b.purchase_price || 0), 0);
  const authenticatedBindings = items.filter((b) => b.binding_authenticated).length;

  return {
    totalItems,
    totalVolumes,
    totalValueLow,
    totalValueMid,
    totalValueHigh,
    totalPurchaseCost,
    authenticatedBindings,
  };
});

// Sort books by value (highest first)
const sortedBooks = computed(() => {
  return [...filteredBooks.value].sort(
    (a, b) => Number(b.value_mid || 0) - Number(a.value_mid || 0)
  );
});

// Report title based on type
const reportTitle = computed(() => {
  switch (reportType.value) {
    case "insurance":
      return "Insurance Valuation Report";
    case "primary":
      return "Primary Collection Inventory";
    case "extended":
      return "Extended Collection Inventory";
    case "all":
      return "Complete Collection Inventory";
    default:
      return "Collection Report";
  }
});

// Summary label based on type
const summaryLabel = computed(() => {
  switch (reportType.value) {
    case "insurance":
      return "On Hand Only";
    case "primary":
      return "Primary Collection";
    case "extended":
      return "Extended Collection";
    case "all":
      return "All Items";
    default:
      return "";
  }
});

// Show insurance-specific elements
const isInsuranceReport = computed(() => reportType.value === "insurance");

// Format currency (handles string values from API Decimal fields)
const formatCurrency = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined) return "-";
  const numValue = Number(value);
  if (isNaN(numValue)) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(numValue);
};

// Format date for display
const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return "-";
  if (/^\d{4}$/.test(dateStr)) return dateStr;
  if (/^\d{4}-\d{4}$/.test(dateStr)) return dateStr;
  try {
    const date = new Date(dateStr);
    return date.getFullYear().toString();
  } catch {
    return dateStr;
  }
};

// Get today's date for report header
const reportDate = new Date().toLocaleDateString("en-US", {
  year: "numeric",
  month: "long",
  day: "numeric",
});

// Print function
const printReport = () => {
  window.print();
};

// Compute era from year_start
const computeEra = (yearStart: number | null | undefined): string => {
  if (!yearStart) return "";
  if (yearStart >= 1837 && yearStart <= 1850) return "Victorian Early";
  if (yearStart >= 1851 && yearStart <= 1870) return "Victorian Mid";
  if (yearStart >= 1871 && yearStart <= 1901) return "Victorian Late";
  // For non-Victorian years, return decade (e.g., "1920s")
  const decade = Math.floor(yearStart / 10) * 10;
  return `${decade}s`;
};

// Format ISO date to YYYY-MM-DD
const formatISODate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return "";
  // Extract just the date portion from ISO format
  return dateStr.split("T")[0];
};

// CSV Export function
const exportCSV = () => {
  const headers = [
    "Title",
    "Author",
    "Publisher",
    "Publisher Tier",
    "Publication Date",
    "Edition",
    "Volumes",
    "Category",
    "Inventory Type",
    "Binder",
    "Binding Authenticated",
    "Binding Type",
    "Binding Description",
    "Condition Grade",
    "Condition Notes",
    "Value Low",
    "Value Mid",
    "Value High",
    "Purchase Price",
    "Acquisition Cost",
    "Purchase Date",
    "Purchase Source",
    "Discount %",
    "ROI %",
    "Status",
    "Notes",
    "Provenance",
    "First Edition",
    "Has Provenance",
    "Provenance Tier",
    "Year Start",
    "Year End",
    "Era",
    "Complete Set",
    "Overall Score",
    "Source URL",
    "Created At",
  ];

  const escapeCSV = (val: string | null | undefined): string => {
    if (val === null || val === undefined) return "";
    return `"${String(val).replace(/"/g, '""')}"`;
  };

  const rows = sortedBooks.value.map((book) => [
    escapeCSV(book.title),
    escapeCSV(book.author?.name),
    escapeCSV(book.publisher?.name),
    escapeCSV(book.publisher?.tier),
    escapeCSV(book.publication_date),
    escapeCSV(book.edition),
    book.volumes || 1,
    escapeCSV(book.category),
    escapeCSV(book.inventory_type),
    escapeCSV(book.binder?.name),
    book.binding_authenticated ? "Yes" : "No",
    escapeCSV(book.binding_type),
    escapeCSV(book.binding_description),
    escapeCSV(book.condition_grade),
    escapeCSV(book.condition_notes),
    book.value_low || "",
    book.value_mid || "",
    book.value_high || "",
    book.purchase_price || "",
    book.acquisition_cost || "",
    escapeCSV(book.purchase_date),
    escapeCSV(book.purchase_source),
    book.discount_pct || "",
    book.roi_pct || "",
    escapeCSV(book.status),
    escapeCSV(book.notes),
    escapeCSV(book.provenance),
    book.is_first_edition ? "Yes" : "No",
    book.has_provenance ? "Yes" : "No",
    escapeCSV(book.provenance_tier),
    book.year_start || "",
    book.year_end || "",
    escapeCSV(computeEra(book.year_start)),
    book.is_complete ? "Yes" : "No",
    book.overall_score || "",
    escapeCSV(book.source_url),
    escapeCSV(formatISODate(book.created_at)),
  ]);

  const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");

  // Filename based on report type
  const typeSlug = reportType.value === "insurance" ? "insurance" : `inventory_${reportType.value}`;
  const filename = `book_collection_${typeSlug}_${new Date().toISOString().split("T")[0]}.csv`;

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
</script>

<template>
  <div class="max-w-6xl mx-auto p-8 font-display">
    <!-- Action buttons (hidden when printing) -->
    <div class="no-print flex items-center gap-4 mb-8 pb-4 border-b border-victorian-paper-antique">
      <router-link to="/books" class="btn-secondary shrink-0"> ← Back to Collection </router-link>

      <!-- Report Type Selector -->
      <div class="flex items-center gap-2 flex-1">
        <label for="reportType" class="font-semibold text-victorian-ink-dark whitespace-nowrap"
          >Report Type:</label
        >
        <select id="reportType" v-model="reportType" :disabled="loading" class="select">
          <option v-for="opt in reportTypeOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <span class="text-sm text-victorian-ink-muted italic whitespace-nowrap">{{
          reportTypeOptions.find((o) => o.value === reportType)?.description
        }}</span>
      </div>

      <div class="flex gap-2 shrink-0">
        <button class="btn-secondary" :disabled="loading" @click="exportCSV">Export CSV</button>
        <button class="btn-primary" :disabled="loading" @click="printReport">Print Report</button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center p-12 text-lg text-victorian-ink-muted">
      Loading collection data...
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center p-12 text-lg text-victorian-burgundy">
      {{ error }}
    </div>

    <!-- Report content -->
    <template v-else>
      <!-- Report Header -->
      <header class="text-center mb-8 pb-4 border-b-2 border-victorian-hunter-800">
        <h1 class="text-3xl text-victorian-hunter-900 mb-1 font-display">
          Victorian Book Collection
        </h1>
        <h2 class="text-xl text-victorian-ink-dark font-normal mb-2">{{ reportTitle }}</h2>
        <p class="text-victorian-ink-muted text-sm">Generated: {{ reportDate }}</p>
      </header>

      <!-- Collection Summary -->
      <section class="card-static mb-8">
        <h3 class="mt-0 mb-4 text-victorian-ink-dark font-display text-lg">
          Collection Summary ({{ summaryLabel }})
        </h3>
        <div class="grid grid-cols-4 gap-4 mb-4 max-md:grid-cols-2">
          <div
            class="bg-victorian-paper-white p-4 rounded-sm text-center border border-victorian-paper-antique"
          >
            <span class="block text-xs text-victorian-ink-muted mb-1">Collections</span>
            <span class="block text-2xl font-bold">{{ stats.totalItems }}</span>
          </div>
          <div
            class="bg-victorian-paper-white p-4 rounded-sm text-center border border-victorian-paper-antique"
          >
            <span class="block text-xs text-victorian-ink-muted mb-1">Volumes</span>
            <span class="block text-2xl font-bold">{{ stats.totalVolumes }}</span>
          </div>
          <div
            class="bg-victorian-paper-white p-4 rounded-sm text-center border border-victorian-paper-antique"
          >
            <span class="block text-xs text-victorian-ink-muted mb-1">Authenticated Bindings</span>
            <span class="block text-2xl font-bold">{{ stats.authenticatedBindings }}</span>
          </div>
          <div
            class="bg-victorian-paper-white p-4 rounded-sm text-center border border-victorian-paper-antique"
          >
            <span class="block text-xs text-victorian-ink-muted mb-1">Total Cost</span>
            <span class="block text-2xl font-bold">{{
              formatCurrency(stats.totalPurchaseCost)
            }}</span>
          </div>
          <div
            class="bg-victorian-gold-muted/20 p-4 rounded-sm text-center border border-victorian-gold-muted"
          >
            <span class="block text-xs text-victorian-ink-muted mb-1">Low Estimate</span>
            <span class="block text-2xl font-bold">{{ formatCurrency(stats.totalValueLow) }}</span>
          </div>
          <div
            class="bg-victorian-hunter-800 text-white p-4 rounded-sm text-center border border-victorian-hunter-800"
          >
            <span class="block text-xs text-victorian-paper-cream mb-1">Mid Estimate</span>
            <span class="block text-2xl font-bold">{{ formatCurrency(stats.totalValueMid) }}</span>
          </div>
          <div
            class="bg-victorian-gold-muted/20 p-4 rounded-sm text-center border border-victorian-gold-muted"
          >
            <span class="block text-xs text-victorian-ink-muted mb-1">High Estimate</span>
            <span class="block text-2xl font-bold">{{ formatCurrency(stats.totalValueHigh) }}</span>
          </div>
        </div>
        <!-- Insurance recommendation only for insurance report -->
        <p
          v-if="isInsuranceReport"
          class="bg-[var(--color-status-success-bg)] p-4 rounded-sm text-center m-0 border border-[var(--color-status-success-border)]"
        >
          <strong>Recommended Insurance Coverage:</strong>
          {{ formatCurrency(stats.totalValueHigh * 1.1) }}
          <span class="text-sm text-[var(--color-status-success-text)]"
            >(High estimate + 10% buffer)</span
          >
        </p>
      </section>

      <!-- Itemized List -->
      <section class="mb-8">
        <h3 class="mb-4 text-victorian-ink-dark font-display text-lg">
          Itemized Collection ({{ sortedBooks.length }} items, sorted by value)
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th class="bg-victorian-hunter-800 text-white font-semibold p-2 text-left w-1/4">
                  Title
                </th>
                <th
                  class="bg-victorian-hunter-800 text-white font-semibold p-2 text-left w-[12%] max-md:hidden"
                >
                  Author
                </th>
                <th
                  class="bg-victorian-hunter-800 text-white font-semibold p-2 text-left w-[15%] max-md:hidden"
                >
                  Publisher
                </th>
                <th class="bg-victorian-hunter-800 text-white font-semibold p-2 text-center w-[8%]">
                  Year
                </th>
                <th class="bg-victorian-hunter-800 text-white font-semibold p-2 text-center w-[5%]">
                  Vols
                </th>
                <th class="bg-victorian-hunter-800 text-white font-semibold p-2 text-left w-[14%]">
                  Binder
                </th>
                <th class="bg-victorian-hunter-800 text-white font-semibold p-2 text-center w-[8%]">
                  Condition
                </th>
                <th class="bg-victorian-hunter-800 text-white font-semibold p-2 text-right w-[13%]">
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="book in sortedBooks"
                :key="book.id"
                :class="[
                  book.binding_authenticated
                    ? 'bg-victorian-gold-muted/10 border-b border-victorian-gold-muted'
                    : 'even:bg-victorian-paper-cream border-b border-victorian-paper-antique',
                ]"
              >
                <td class="p-2">{{ book.title }}</td>
                <td class="p-2 max-md:hidden">{{ book.author?.name || "-" }}</td>
                <td class="p-2 max-md:hidden">
                  {{ book.publisher?.name || "-" }}
                  <span
                    v-if="book.publisher?.tier"
                    class="text-xs bg-victorian-paper-aged px-1 py-0.5 rounded-sm ml-1 text-victorian-ink-dark"
                    >{{ book.publisher.tier }}</span
                  >
                </td>
                <td class="p-2 text-center">{{ formatDate(book.publication_date) }}</td>
                <td class="p-2 text-center">{{ book.volumes || 1 }}</td>
                <td class="p-2">
                  <span v-if="book.binding_authenticated" class="text-victorian-gold-dark">★</span>
                  {{ book.binder?.name || "-" }}
                </td>
                <td class="p-2 text-center">{{ book.condition_grade || "-" }}</td>
                <td class="p-2 text-right">{{ formatCurrency(book.value_mid) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="bg-victorian-hunter-800 text-white">
                <td colspan="4" class="p-3 border-0"><strong>TOTAL</strong></td>
                <td class="p-3 border-0 text-center">
                  <strong>{{ stats.totalVolumes }}</strong>
                </td>
                <td colspan="2" class="p-3 border-0"></td>
                <td class="p-3 border-0 text-right">
                  <strong>{{ formatCurrency(stats.totalValueMid) }}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <!-- Footer -->
      <footer
        class="text-center text-victorian-ink-muted text-sm pt-4 border-t border-victorian-paper-antique"
      >
        <p v-if="isInsuranceReport">
          This report is for insurance valuation purposes. Values are estimates based on current
          market conditions.
        </p>
        <p v-else>Inventory export generated from BlueMoxon collection database.</p>
        <p class="italic">
          ★ = Authenticated premium binding (Rivière, Zaehnsdorf, Sangorski & Sutcliffe, Bayntun)
        </p>
        <p class="italic">
          Tier 1 publishers: Smith Elder, Moxon, Macmillan, John Murray, Chapman & Hall
        </p>
      </footer>
    </template>
  </div>
</template>

<style scoped>
/* Print styles only - all other styling uses Tailwind classes */
@media print {
  .no-print {
    display: none !important;
  }

  /* Override Tailwind for print optimization */
  .max-w-6xl {
    max-width: none !important;
    padding: 0 !important;
  }

  /* Ensure tables and content fit on pages */
  table {
    font-size: 0.7rem !important;
  }

  th,
  td {
    padding: 0.25rem 0.4rem !important;
  }

  tr {
    break-inside: avoid;
  }

  thead {
    display: table-header-group;
  }

  tfoot {
    display: table-footer-group;
  }

  /* Force black text for readability */
  .bg-victorian-hunter-800 {
    background-color: white !important;
    color: black !important;
    border: 2px solid #1a3a2f !important;
  }

  .text-white {
    color: black !important;
  }

  .text-victorian-paper-cream {
    color: #4a5568 !important;
  }

  /* Ensure summary cards print correctly */
  .card-static {
    padding: 1rem !important;
    margin-bottom: 1rem !important;
    break-inside: avoid;
  }

  /* Footer spacing */
  footer {
    margin-top: 1rem;
    font-size: 0.7rem;
  }

  /* Authenticated rows should still be visible */
  .bg-victorian-gold-muted\/10 {
    background-color: #fff8f0 !important;
  }

  .even\:bg-victorian-paper-cream:nth-child(even) {
    background-color: #f5f5f5 !important;
  }
}
</style>
