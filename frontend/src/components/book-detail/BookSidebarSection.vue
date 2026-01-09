<script setup lang="ts">
import { computed } from "vue";
import type { Book } from "@/stores/books";
import ArchiveStatusBadge from "@/components/ArchiveStatusBadge.vue";
import TrackingCard from "@/components/TrackingCard.vue";
import { BOOK_STATUSES } from "@/constants";

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

function formatDate(dateString: string | null): string {
  if (!dateString) return "-";
  // Parse as local date to avoid timezone issues with date-only strings
  const [year, month, day] = dateString.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const hasScores = computed(() => {
  return (
    props.book.overall_score !== null ||
    props.book.investment_grade !== null ||
    props.book.strategic_fit !== null ||
    props.book.collection_impact !== null
  );
});

const isInTransit = computed(() => {
  return props.book.status === BOOK_STATUSES.IN_TRANSIT;
});
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
        <div v-if="props.book.purchase_date">
          <dt class="text-sm text-gray-500">Purchase Date</dt>
          <dd class="font-medium">
            {{ formatDate(props.book.purchase_date) }}
          </dd>
        </div>
        <div v-if="props.book.purchase_source">
          <dt class="text-sm text-gray-500">Source</dt>
          <dd class="font-medium">
            {{ props.book.purchase_source }}
          </dd>
        </div>
      </dl>
    </div>

    <!-- Scoring Card -->
    <div v-if="hasScores" class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Scoring</h2>
      <dl class="flex flex-col gap-2 text-sm">
        <div v-if="props.book.overall_score !== null" class="flex justify-between">
          <dt class="text-gray-500">Overall Score</dt>
          <dd class="font-medium">{{ props.book.overall_score }}</dd>
        </div>
        <div v-if="props.book.investment_grade !== null" class="flex justify-between">
          <dt class="text-gray-500">Investment Grade</dt>
          <dd class="font-medium">{{ props.book.investment_grade }}</dd>
        </div>
        <div v-if="props.book.strategic_fit !== null" class="flex justify-between">
          <dt class="text-gray-500">Strategic Fit</dt>
          <dd class="font-medium">{{ props.book.strategic_fit }}</dd>
        </div>
        <div v-if="props.book.collection_impact !== null" class="flex justify-between">
          <dt class="text-gray-500">Collection Impact</dt>
          <dd class="font-medium">{{ props.book.collection_impact }}</dd>
        </div>
      </dl>
    </div>

    <!-- Tracking Card (only for IN_TRANSIT books) -->
    <TrackingCard
      v-if="isInTransit"
      :book-id="props.book.id"
      :tracking-status="props.book.tracking_status"
      :tracking-carrier="props.book.tracking_carrier"
      :tracking-number="props.book.tracking_number"
      :tracking-url="props.book.tracking_url"
      :tracking-last-checked="props.book.tracking_last_checked"
      :estimated-delivery="props.book.estimated_delivery"
    />

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
