<script setup lang="ts">
import { ref, computed } from "vue";
import { api } from "@/services/api";
import { formatBytes, formatCost } from "@/utils/format";
import { useCleanupJobPolling } from "@/composables/useCleanupJobPolling";

interface OrphanGroup {
  folder_id: number;
  book_id: number | null;
  book_title: string | null;
  count: number;
  bytes: number;
  keys: string[];
}

interface ScanResult {
  total_count: number;
  total_bytes: number;
  orphans_by_book: OrphanGroup[];
}

const scanResult = ref<ScanResult | null>(null);
const scanning = ref(false);
const scanError = ref<string | null>(null);
const detailsExpanded = ref(false);
const confirmingDelete = ref(false);
const deleting = ref(false);
const deleteComplete = ref(false);
const deleteSummary = ref<{ count: number; bytes: number } | null>(null);

const {
  isActive: jobActive,
  progressPct,
  deletedCount,
  deletedBytes,
  status: _status,
  error: jobError,
  start: startPolling,
} = useCleanupJobPolling({
  onComplete: (data) => {
    deleting.value = false;
    deleteComplete.value = true;
    deleteSummary.value = {
      count: data.deleted_count,
      bytes: data.deleted_bytes,
    };
  },
  onError: () => {
    deleting.value = false;
  },
});

const hasOrphans = computed(() => {
  return scanResult.value && scanResult.value.total_count > 0;
});

const isWorking = computed(() => {
  return scanning.value || deleting.value || jobActive.value;
});

async function scan() {
  scanning.value = true;
  scanError.value = null;
  scanResult.value = null;
  deleteComplete.value = false;
  deleteSummary.value = null;
  try {
    const response = await api.get("/admin/cleanup/orphans/scan");
    scanResult.value = response.data;
  } catch (e: unknown) {
    const axiosErr = e as { response?: { data?: { detail?: string } }; message?: string };
    scanError.value =
      axiosErr.response?.data?.detail || axiosErr.message || "Failed to scan for orphans";
  } finally {
    scanning.value = false;
  }
}

async function startDelete() {
  if (!scanResult.value) return;
  deleting.value = true;
  confirmingDelete.value = false;

  try {
    const response = await api.post("/admin/cleanup/orphans/delete", {
      total_count: scanResult.value.total_count,
      total_bytes: scanResult.value.total_bytes,
    });

    startPolling(response.data.job_id);
  } catch (e: unknown) {
    deleting.value = false;
    const axiosErr = e as { response?: { data?: { detail?: string } }; message?: string };
    scanError.value =
      axiosErr.response?.data?.detail || axiosErr.message || "Failed to start delete job";
  }
}

function reset() {
  scanResult.value = null;
  deleteComplete.value = false;
  deleteSummary.value = null;
  confirmingDelete.value = false;
  scanError.value = null;
}
</script>

<template>
  <div class="orphan-cleanup-panel">
    <!-- Header -->
    <h3 class="text-lg font-semibold text-gray-800 mb-4">Orphaned Images Cleanup</h3>

    <!-- Initial state: Scan buttons -->
    <div v-if="!scanResult && !deleteComplete" class="space-y-4">
      <p class="text-sm text-gray-600">
        Scan for orphaned images that are no longer referenced by any book. These files consume
        storage space but serve no purpose.
      </p>

      <div class="flex gap-3">
        <button
          data-testid="scan-button"
          :disabled="isWorking"
          class="px-4 py-2 bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          @click="scan"
        >
          <span v-if="scanning" class="flex items-center gap-2">
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            Scanning...
          </span>
          <span v-else>Scan for Orphans</span>
        </button>
      </div>

      <!-- Scan error -->
      <div
        v-if="scanError"
        class="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700"
      >
        {{ scanError }}
      </div>
    </div>

    <!-- Scan results -->
    <div v-if="scanResult && !deleteComplete" class="space-y-4">
      <!-- Summary stats -->
      <div
        v-if="hasOrphans"
        data-testid="scan-results"
        class="p-4 bg-amber-50 border border-amber-200 rounded"
      >
        <div class="flex items-center gap-2 mb-2">
          <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span class="font-medium text-amber-800">Orphaned Images Found</span>
        </div>
        <div class="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span class="text-gray-600">Files:</span>
            <span class="ml-2 font-medium" data-testid="orphan-count">{{
              scanResult.total_count
            }}</span>
          </div>
          <div>
            <span class="text-gray-600">Size:</span>
            <span class="ml-2 font-medium" data-testid="orphan-size">{{
              formatBytes(scanResult.total_bytes)
            }}</span>
          </div>
          <div>
            <span class="text-gray-600">Est. Cost:</span>
            <span class="ml-2 font-medium" data-testid="orphan-cost">{{
              formatCost(scanResult.total_bytes)
            }}</span>
          </div>
        </div>
      </div>

      <!-- No orphans found -->
      <div
        v-else
        data-testid="no-orphans"
        class="p-4 bg-green-50 border border-green-200 rounded text-green-700"
      >
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M5 13l4 4L19 7"
            />
          </svg>
          <span>No orphaned images found. Storage is clean.</span>
        </div>
      </div>

      <!-- Expandable details -->
      <div v-if="hasOrphans">
        <button
          data-testid="toggle-details"
          class="text-sm text-victorian-hunter-600 hover:text-victorian-hunter-700 flex items-center gap-1"
          @click="detailsExpanded = !detailsExpanded"
        >
          <svg
            class="w-4 h-4 transition-transform"
            :class="{ 'rotate-90': detailsExpanded }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5l7 7-7 7"
            />
          </svg>
          {{ detailsExpanded ? "Hide Details" : "Show Details" }}
        </button>

        <div
          v-if="detailsExpanded"
          data-testid="orphan-details"
          class="mt-3 max-h-64 overflow-y-auto border border-gray-200 rounded"
        >
          <table class="w-full text-sm">
            <thead class="bg-gray-50 sticky top-0">
              <tr class="text-left">
                <th class="px-3 py-2 font-medium text-gray-600">Book</th>
                <th class="px-3 py-2 font-medium text-gray-600 text-right">Files</th>
                <th class="px-3 py-2 font-medium text-gray-600 text-right">Size</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="group in scanResult.orphans_by_book"
                :key="group.folder_id"
                class="border-t border-gray-100"
              >
                <td class="px-3 py-2">
                  <span v-if="group.book_title">{{ group.book_title }}</span>
                  <span v-else class="text-gray-400 italic"
                    >Deleted book (ID: {{ group.book_id || group.folder_id }})</span
                  >
                </td>
                <td class="px-3 py-2 text-right tabular-nums">{{ group.count }}</td>
                <td class="px-3 py-2 text-right tabular-nums">{{ formatBytes(group.bytes) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Action buttons -->
      <div v-if="hasOrphans" class="flex gap-3 pt-2">
        <!-- Delete confirmation inline -->
        <div v-if="confirmingDelete" class="flex items-center gap-3">
          <span class="text-sm text-gray-600">Delete all orphaned images?</span>
          <button
            data-testid="confirm-delete"
            class="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
            @click="startDelete"
          >
            Yes, Delete
          </button>
          <button
            data-testid="cancel-delete"
            class="px-3 py-1.5 border border-gray-300 text-gray-600 text-sm rounded hover:bg-gray-50 transition-colors"
            @click="confirmingDelete = false"
          >
            Cancel
          </button>
        </div>

        <template v-else>
          <button
            data-testid="delete-button"
            :disabled="isWorking"
            class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            @click="confirmingDelete = true"
          >
            Delete Orphans
          </button>
          <button
            class="px-4 py-2 border border-gray-300 text-gray-600 rounded hover:bg-gray-50 transition-colors"
            @click="reset"
          >
            Cancel
          </button>
        </template>
      </div>

      <!-- Rescan button when no orphans -->
      <div v-else class="flex gap-3 pt-2">
        <button
          class="px-4 py-2 border border-gray-300 text-gray-600 rounded hover:bg-gray-50 transition-colors"
          @click="reset"
        >
          Done
        </button>
      </div>
    </div>

    <!-- Progress during deletion -->
    <div v-if="deleting || jobActive" data-testid="delete-progress" class="space-y-4">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 animate-spin text-victorian-hunter-600" fill="none" viewBox="0 0 24 24">
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          ></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        <span class="font-medium text-gray-700">Deleting orphaned images...</span>
      </div>

      <!-- Progress bar -->
      <div class="relative h-4 bg-gray-200 rounded overflow-hidden">
        <div
          data-testid="progress-bar"
          class="absolute inset-y-0 left-0 bg-victorian-hunter-600 transition-all duration-300"
          :style="{ width: `${progressPct}%` }"
        ></div>
        <div class="absolute inset-0 flex items-center justify-center text-xs font-medium">
          {{ progressPct }}%
        </div>
      </div>

      <div class="text-sm text-gray-600">
        Deleted {{ deletedCount }} files ({{ formatBytes(deletedBytes) }})
      </div>

      <!-- Job error -->
      <div v-if="jobError" class="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
        {{ jobError }}
      </div>
    </div>

    <!-- Completion summary -->
    <div v-if="deleteComplete && deleteSummary" data-testid="delete-complete" class="space-y-4">
      <div class="p-4 bg-green-50 border border-green-200 rounded">
        <div class="flex items-center gap-2 mb-2">
          <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M5 13l4 4L19 7"
            />
          </svg>
          <span class="font-medium text-green-800">Cleanup Complete</span>
        </div>
        <div class="text-sm text-green-700">
          Successfully deleted {{ deleteSummary.count }} orphaned images, freeing
          {{ formatBytes(deleteSummary.bytes) }} of storage.
        </div>
      </div>

      <button
        data-testid="done-button"
        class="px-4 py-2 bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700 transition-colors"
        @click="reset"
      >
        Done
      </button>
    </div>
  </div>
</template>
