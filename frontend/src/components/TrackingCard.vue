<script setup lang="ts">
import { ref, computed } from "vue";
import { api } from "@/services/api";

interface Props {
  bookId: number;
  trackingStatus?: string | null;
  trackingCarrier?: string | null;
  trackingNumber?: string | null;
  trackingUrl?: string | null;
  trackingLastChecked?: string | null;
  estimatedDelivery?: string | null;
  trackingActive?: boolean;
  trackingDeliveredAt?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
  trackingActive: false,
});

const emit = defineEmits<{
  refreshed: [data: Record<string, unknown>];
}>();

const refreshing = ref(false);
const errorMessage = ref<string | null>(null);

const hasTracking = computed(() => {
  return props.trackingNumber || props.trackingUrl || props.trackingStatus;
});

const isDelivered = computed(() => {
  return !props.trackingActive && props.trackingStatus?.toLowerCase().includes("delivered");
});

const showRefreshButton = computed(() => {
  return hasTracking.value && props.trackingActive && !isDelivered.value;
});

const statusColorClass = computed(() => {
  const status = props.trackingStatus?.toLowerCase() || "";

  if (status.includes("delivered")) {
    return "bg-green-100 text-green-800";
  }
  if (status.includes("delay") || status.includes("exception") || status.includes("problem")) {
    return "bg-yellow-100 text-yellow-800";
  }
  if (status.includes("transit") || status.includes("shipping")) {
    return "bg-victorian-hunter-100 text-victorian-hunter-800";
  }
  if (status.includes("out for delivery")) {
    return "bg-blue-100 text-blue-800";
  }
  // Default for pending, label created, etc.
  return "bg-gray-100 text-gray-700";
});

function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
}

async function handleRefresh() {
  if (refreshing.value) return;

  refreshing.value = true;
  errorMessage.value = null;

  try {
    const response = await api.post(`/books/${props.bookId}/tracking/refresh`);
    emit("refreshed", response.data);
  } catch (e: unknown) {
    const error = e as { message?: string };
    errorMessage.value = error.message || "Failed to refresh tracking";
  } finally {
    refreshing.value = false;
  }
}
</script>

<template>
  <div class="border rounded-lg p-3 bg-white">
    <!-- No Tracking State -->
    <div v-if="!hasTracking" class="text-center py-2">
      <svg
        class="w-8 h-8 mx-auto text-gray-300 mb-2"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.5"
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
        />
      </svg>
      <p class="text-sm text-gray-500">No tracking information available</p>
    </div>

    <!-- Tracking Info -->
    <div v-else>
      <!-- Header with Status -->
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm font-medium text-gray-600 uppercase">Tracking</span>
        <span
          v-if="trackingStatus"
          data-testid="tracking-status"
          :class="[statusColorClass, 'px-2 py-1 rounded-sm text-xs font-semibold']"
        >
          {{ trackingStatus }}
        </span>
      </div>

      <!-- Carrier and Number -->
      <div class="flex flex-col gap-2 text-sm">
        <div v-if="trackingCarrier" class="flex justify-between items-center">
          <span class="text-gray-600">Carrier</span>
          <span class="font-medium">{{ trackingCarrier }}</span>
        </div>

        <div v-if="trackingNumber" class="flex justify-between items-center">
          <span class="text-gray-600">Number</span>
          <div class="flex items-center gap-1">
            <a
              v-if="trackingUrl"
              :href="trackingUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="font-medium link hover:underline flex items-center gap-1"
            >
              <span class="font-mono text-xs">{{ trackingNumber }}</span>
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
            <span v-else class="font-mono text-xs">{{ trackingNumber }}</span>
          </div>
        </div>

        <!-- Estimated Delivery -->
        <div v-if="estimatedDelivery" class="flex justify-between items-center">
          <span class="text-gray-600">Est. Delivery</span>
          <span class="font-medium">{{ formatDate(estimatedDelivery) }}</span>
        </div>

        <!-- Delivered At -->
        <div v-if="isDelivered && trackingDeliveredAt" class="flex justify-between items-center">
          <span class="text-gray-600">Delivered</span>
          <span class="font-medium text-green-700">{{ formatDate(trackingDeliveredAt) }}</span>
        </div>
      </div>

      <!-- Last Checked & Refresh -->
      <div class="mt-3 pt-2 border-t flex items-center justify-between">
        <span v-if="trackingLastChecked" class="text-xs text-gray-500">
          Last checked {{ formatRelativeTime(trackingLastChecked) }}
        </span>
        <span v-else class="text-xs text-gray-500"></span>

        <button
          v-if="showRefreshButton"
          data-testid="refresh-button"
          @click="handleRefresh"
          :disabled="refreshing"
          class="text-xs link hover:underline flex items-center gap-1 disabled:opacity-50"
        >
          <svg
            :class="['w-3 h-3', { 'animate-spin': refreshing }]"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {{ refreshing ? "Refreshing..." : "Refresh" }}
        </button>
      </div>

      <!-- Error Message -->
      <div
        v-if="errorMessage"
        class="mt-2 text-xs text-[var(--color-status-error-text)] bg-[var(--color-status-error-bg)] p-2 rounded"
      >
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>
