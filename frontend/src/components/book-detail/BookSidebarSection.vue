<script setup lang="ts">
import type { Book } from "@/stores/books";
import ArchiveStatusBadge from "@/components/ArchiveStatusBadge.vue";

interface Props {
  book: Book;
  imageCount: number;
}

const props = defineProps<Props>();

function formatCurrency(value: number | null): string {
  if (value === null) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  }).format(value);
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Valuation Card -->
    <div class="card bg-victorian-cream">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Valuation</h2>
      <div class="text-center">
        <p class="text-3xl font-bold text-victorian-gold">
          {{ formatCurrency(props.book.value_mid) }}
        </p>
        <p class="text-sm text-gray-500 mt-1">Mid Estimate</p>
      </div>
      <div class="flex justify-between mt-4 text-sm">
        <div class="text-center">
          <p class="font-medium">
            {{ formatCurrency(props.book.value_low) }}
          </p>
          <p class="text-gray-500">Low</p>
        </div>
        <div class="text-center">
          <p class="font-medium">
            {{ formatCurrency(props.book.value_high) }}
          </p>
          <p class="text-gray-500">High</p>
        </div>
      </div>
      <!-- Purchase Price -->
      <div v-if="props.book.purchase_price" class="mt-4 pt-4 border-t border-gray-200">
        <div class="text-center">
          <p class="text-xl font-semibold text-gray-700">
            {{ formatCurrency(props.book.purchase_price) }}
          </p>
          <p class="text-sm text-gray-500">Purchase Price</p>
        </div>
      </div>
    </div>

    <!-- Acquisition Card -->
    <div v-if="props.book.purchase_price" class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Acquisition</h2>
      <dl class="flex flex-col gap-2">
        <div>
          <dt class="text-sm text-gray-500">Purchase Price</dt>
          <dd class="font-medium">
            {{ formatCurrency(props.book.purchase_price) }}
          </dd>
        </div>
        <div v-if="props.book.acquisition_cost">
          <dt class="text-sm text-gray-500">Acquisition Cost</dt>
          <dd class="font-medium">
            {{ formatCurrency(props.book.acquisition_cost) }}
            <span class="text-xs text-gray-400">(incl. shipping/tax)</span>
          </dd>
        </div>
        <div v-if="props.book.discount_pct">
          <dt class="text-sm text-gray-500">Discount</dt>
          <dd class="font-medium text-[var(--color-status-success-accent)]">
            {{ props.book.discount_pct }}%
          </dd>
        </div>
        <div v-if="props.book.roi_pct">
          <dt class="text-sm text-gray-500">ROI</dt>
          <dd class="font-medium text-[var(--color-status-success-accent)]">
            {{ props.book.roi_pct }}%
          </dd>
        </div>
      </dl>
    </div>

    <!-- Source Archive Card -->
    <div v-if="props.book.source_url" class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Source Archive</h2>
      <dl class="flex flex-col gap-3">
        <div>
          <dt class="text-sm text-gray-500">Original Listing</dt>
          <dd class="font-medium truncate">
            <a
              :href="props.book.source_url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-moxon-600 hover:text-moxon-800 hover:underline"
              :title="props.book.source_url"
            >
              View Source
            </a>
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500 mb-1">Archive Status</dt>
          <dd>
            <ArchiveStatusBadge
              :status="props.book.archive_status"
              :archived-url="props.book.source_archived_url"
            />
          </dd>
        </div>
      </dl>
    </div>

    <!-- Quick Info Card -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Quick Info</h2>
      <dl class="flex flex-col gap-2 text-sm">
        <div class="flex justify-between">
          <dt class="text-gray-500">Images</dt>
          <dd class="font-medium">{{ props.imageCount }}</dd>
        </div>
        <div class="flex justify-between">
          <dt class="text-gray-500">Has Analysis</dt>
          <dd class="font-medium">{{ props.book.has_analysis ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex justify-between">
          <dt class="text-gray-500">Inventory Type</dt>
          <dd class="font-medium">
            {{ props.book.inventory_type }}
          </dd>
        </div>
      </dl>
    </div>
  </div>
</template>
