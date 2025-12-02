<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { api } from "@/services/api";
import type { Book } from "@/stores/books";

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
        per_page: 100,
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
    return books.value.filter((book) => book.status === "ON_HAND");
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
    "Purchase Date",
    "Purchase Source",
    "Discount %",
    "ROI %",
    "Status",
    "Notes",
    "Provenance",
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
    escapeCSV(book.purchase_date),
    escapeCSV(book.purchase_source),
    book.discount_pct || "",
    book.roi_pct || "",
    escapeCSV(book.status),
    escapeCSV(book.notes),
    escapeCSV(book.provenance),
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
  <div class="insurance-report">
    <!-- Action buttons (hidden when printing) -->
    <div class="actions no-print">
      <router-link to="/books" class="btn btn-secondary"> ← Back to Collection </router-link>

      <!-- Report Type Selector -->
      <div class="report-type-selector">
        <label for="reportType">Report Type:</label>
        <select id="reportType" v-model="reportType" :disabled="loading">
          <option v-for="opt in reportTypeOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <span class="report-type-desc">{{
          reportTypeOptions.find((o) => o.value === reportType)?.description
        }}</span>
      </div>

      <div class="action-buttons">
        <button @click="exportCSV" class="btn btn-secondary" :disabled="loading">Export CSV</button>
        <button @click="printReport" class="btn btn-primary" :disabled="loading">
          Print Report
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading">Loading collection data...</div>

    <!-- Error state -->
    <div v-else-if="error" class="error">{{ error }}</div>

    <!-- Report content -->
    <template v-else>
      <!-- Report Header -->
      <header class="report-header">
        <h1>Victorian Book Collection</h1>
        <h2>{{ reportTitle }}</h2>
        <p class="report-date">Generated: {{ reportDate }}</p>
      </header>

      <!-- Collection Summary -->
      <section class="summary">
        <h3>Collection Summary ({{ summaryLabel }})</h3>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">Collections</span>
            <span class="value">{{ stats.totalItems }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Volumes</span>
            <span class="value">{{ stats.totalVolumes }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Authenticated Bindings</span>
            <span class="value">{{ stats.authenticatedBindings }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Total Cost</span>
            <span class="value">{{ formatCurrency(stats.totalPurchaseCost) }}</span>
          </div>
          <div class="summary-item highlight">
            <span class="label">Low Estimate</span>
            <span class="value">{{ formatCurrency(stats.totalValueLow) }}</span>
          </div>
          <div class="summary-item highlight primary">
            <span class="label">Mid Estimate</span>
            <span class="value">{{ formatCurrency(stats.totalValueMid) }}</span>
          </div>
          <div class="summary-item highlight">
            <span class="label">High Estimate</span>
            <span class="value">{{ formatCurrency(stats.totalValueHigh) }}</span>
          </div>
        </div>
        <!-- Insurance recommendation only for insurance report -->
        <p v-if="isInsuranceReport" class="recommendation">
          <strong>Recommended Insurance Coverage:</strong>
          {{ formatCurrency(stats.totalValueHigh * 1.1) }}
          <span class="note">(High estimate + 10% buffer)</span>
        </p>
      </section>

      <!-- Itemized List -->
      <section class="itemized-list">
        <h3>Itemized Collection ({{ sortedBooks.length }} items, sorted by value)</h3>
        <table>
          <thead>
            <tr>
              <th class="col-title">Title</th>
              <th class="col-author">Author</th>
              <th class="col-publisher">Publisher</th>
              <th class="col-year">Year</th>
              <th class="col-vols">Vols</th>
              <th class="col-binder">Binder</th>
              <th class="col-condition">Condition</th>
              <th class="col-value">Value</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="book in sortedBooks"
              :key="book.id"
              :class="{ authenticated: book.binding_authenticated }"
            >
              <td class="col-title">{{ book.title }}</td>
              <td class="col-author">{{ book.author?.name || "-" }}</td>
              <td class="col-publisher">
                {{ book.publisher?.name || "-" }}
                <span v-if="book.publisher?.tier" class="tier-badge">{{
                  book.publisher.tier
                }}</span>
              </td>
              <td class="col-year">{{ formatDate(book.publication_date) }}</td>
              <td class="col-vols">{{ book.volumes || 1 }}</td>
              <td class="col-binder">
                <span v-if="book.binding_authenticated" class="auth-badge">★</span>
                {{ book.binder?.name || "-" }}
              </td>
              <td class="col-condition">{{ book.condition_grade || "-" }}</td>
              <td class="col-value">{{ formatCurrency(book.value_mid) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="total-row">
              <td colspan="4"><strong>TOTAL</strong></td>
              <td>
                <strong>{{ stats.totalVolumes }}</strong>
              </td>
              <td colspan="2"></td>
              <td>
                <strong>{{ formatCurrency(stats.totalValueMid) }}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </section>

      <!-- Footer -->
      <footer class="report-footer">
        <p v-if="isInsuranceReport">
          This report is for insurance valuation purposes. Values are estimates based on current
          market conditions.
        </p>
        <p v-else>Inventory export generated from BlueMoxon collection database.</p>
        <p class="note">
          ★ = Authenticated premium binding (Rivière, Zaehnsdorf, Sangorski & Sutcliffe, Bayntun)
        </p>
        <p class="note">
          Tier 1 publishers: Smith Elder, Moxon, Macmillan, John Murray, Chapman & Hall
        </p>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.insurance-report {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  font-family: "Georgia", serif;
}

/* Loading/Error states */
.loading,
.error {
  text-align: center;
  padding: 3rem;
  font-size: 1.1rem;
}

.error {
  color: #c53030;
}

/* Action buttons */
.actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #ddd;
}

/* Report type selector */
.report-type-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.report-type-selector label {
  font-weight: 600;
  color: #4a5568;
}

.report-type-selector select {
  padding: 0.5rem 1rem;
  border: 1px solid #cbd5e0;
  border-radius: 4px;
  background: white;
  font-size: 0.9rem;
  cursor: pointer;
}

.report-type-selector select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.report-type-desc {
  font-size: 0.8rem;
  color: #718096;
  font-style: italic;
}

.action-buttons {
  display: flex;
  gap: 1rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  text-decoration: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #2c5282;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1a365d;
}

.btn-secondary {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-secondary:hover:not(:disabled) {
  background: #cbd5e0;
}

/* Report Header */
.report-header {
  text-align: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #2c5282;
}

.report-header h1 {
  font-size: 2rem;
  color: #1a365d;
  margin-bottom: 0.25rem;
}

.report-header h2 {
  font-size: 1.25rem;
  color: #4a5568;
  font-weight: normal;
  margin-bottom: 0.5rem;
}

.report-date {
  color: #718096;
  font-size: 0.9rem;
}

/* Summary Section */
.summary {
  background: #f7fafc;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.summary h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #2d3748;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}

.summary-item {
  background: white;
  padding: 1rem;
  border-radius: 4px;
  text-align: center;
  border: 1px solid #e2e8f0;
}

.summary-item.highlight {
  background: #ebf8ff;
  border-color: #90cdf4;
}

.summary-item.primary {
  background: #2c5282;
  color: white;
  border-color: #2c5282;
}

.summary-item .label {
  display: block;
  font-size: 0.8rem;
  color: #718096;
  margin-bottom: 0.25rem;
}

.summary-item.primary .label {
  color: #bee3f8;
}

.summary-item .value {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
}

.recommendation {
  background: #c6f6d5;
  padding: 1rem;
  border-radius: 4px;
  text-align: center;
  margin: 0;
}

.recommendation .note {
  font-size: 0.85rem;
  color: #276749;
}

/* Table */
.itemized-list {
  margin-bottom: 2rem;
}

.itemized-list h3 {
  margin-bottom: 1rem;
  color: #2d3748;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

th,
td {
  padding: 0.5rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

th {
  background: #2c5282;
  color: white;
  font-weight: 600;
}

tr:nth-child(even) {
  background: #f7fafc;
}

tr.authenticated {
  background: #fffaf0;
}

tr.authenticated td {
  border-bottom-color: #f6ad55;
}

.auth-badge {
  color: #dd6b20;
}

.tier-badge {
  font-size: 0.7rem;
  background: #e2e8f0;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  margin-left: 0.25rem;
  color: #4a5568;
}

.total-row {
  background: #2c5282 !important;
  color: white;
}

.total-row td {
  border-bottom: none;
  padding: 0.75rem 0.5rem;
}

/* Column widths */
.col-title {
  width: 25%;
}
.col-author {
  width: 12%;
}
.col-publisher {
  width: 15%;
}
.col-year {
  width: 8%;
  text-align: center;
}
.col-vols {
  width: 5%;
  text-align: center;
}
.col-binder {
  width: 14%;
}
.col-condition {
  width: 8%;
  text-align: center;
}
.col-value {
  width: 13%;
  text-align: right;
}

td.col-year,
td.col-vols,
td.col-condition {
  text-align: center;
}
td.col-value {
  text-align: right;
}

/* Footer */
.report-footer {
  text-align: center;
  color: #718096;
  font-size: 0.85rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.report-footer .note {
  font-style: italic;
}

/* Print styles */
@media print {
  .no-print {
    display: none !important;
  }

  .insurance-report {
    padding: 0;
    max-width: none;
  }

  .report-header {
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
  }

  .summary {
    padding: 1rem;
    margin-bottom: 1rem;
    break-inside: avoid;
  }

  .summary-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
  }

  .summary-item {
    padding: 0.5rem;
  }

  .summary-item .value {
    font-size: 1.1rem;
  }

  table {
    font-size: 0.7rem;
  }

  th,
  td {
    padding: 0.25rem 0.4rem;
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

  .report-footer {
    margin-top: 1rem;
    font-size: 0.7rem;
  }

  .summary-item.highlight,
  .summary-item.primary {
    background: white !important;
    color: black !important;
    border: 2px solid #2c5282 !important;
  }

  .summary-item.primary .label {
    color: #4a5568 !important;
  }

  .recommendation {
    background: white !important;
    border: 2px solid #276749;
  }

  tr.authenticated {
    background: #fff8f0 !important;
  }

  tr:nth-child(even) {
    background: #f5f5f5 !important;
  }

  .tier-badge {
    border: 1px solid #999;
  }
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .actions {
    flex-direction: column;
    align-items: stretch;
  }

  .report-type-selector {
    justify-content: center;
  }

  .action-buttons {
    justify-content: center;
  }

  table {
    font-size: 0.75rem;
  }

  .col-author,
  .col-publisher {
    display: none;
  }
}
</style>
