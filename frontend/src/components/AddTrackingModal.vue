<script setup lang="ts">
import { ref, watch, onUnmounted, computed } from "vue";
import { useAcquisitionsStore, type TrackingPayload } from "@/stores/acquisitions";

const props = defineProps<{
  bookId: number;
  bookTitle: string;
}>();

const emit = defineEmits<{
  close: [];
  added: [];
}>();

const acquisitionsStore = useAcquisitionsStore();

const form = ref<TrackingPayload>({
  tracking_number: "",
  tracking_carrier: "",
  tracking_url: "",
});

const inputMode = ref<"number" | "url">("number");
const submitting = ref(false);
const errorMessage = ref<string | null>(null);

// Show carrier field only when using tracking number and carrier auto-detect might fail
const showCarrierField = computed(() => {
  return inputMode.value === "number" && form.value.tracking_number;
});

// Known carriers for dropdown
const carriers = ["USPS", "UPS", "FedEx", "DHL", "Royal Mail", "Parcelforce", "Other"];

// Lock body scroll when modal is open
watch(
  () => true,
  () => {
    document.body.style.overflow = "hidden";
  },
  { immediate: true }
);

onUnmounted(() => {
  document.body.style.overflow = "";
});

async function handleSubmit() {
  // Validate: need either tracking_number or tracking_url
  if (inputMode.value === "number" && !form.value.tracking_number?.trim()) {
    errorMessage.value = "Please enter a tracking number";
    return;
  }
  if (inputMode.value === "url" && !form.value.tracking_url?.trim()) {
    errorMessage.value = "Please enter a tracking URL";
    return;
  }

  submitting.value = true;
  errorMessage.value = null;

  try {
    const payload: TrackingPayload = {};

    if (inputMode.value === "number") {
      payload.tracking_number = form.value.tracking_number?.trim();
      // Only include carrier if manually specified
      if (form.value.tracking_carrier && form.value.tracking_carrier !== "Other") {
        payload.tracking_carrier = form.value.tracking_carrier;
      }
    } else {
      payload.tracking_url = form.value.tracking_url?.trim();
    }

    await acquisitionsStore.addTracking(props.bookId, payload);
    emit("added");
    emit("close");
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.message || "Failed to add tracking";
    errorMessage.value = detail;
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  if (!submitting.value) {
    emit("close");
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="handleClose"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">Add Tracking</h2>
            <p class="text-sm text-gray-600 truncate">{{ bookTitle }}</p>
          </div>
          <button
            @click="handleClose"
            :disabled="submitting"
            class="text-gray-500 hover:text-gray-700 disabled:opacity-50"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSubmit" class="p-4 flex flex-col gap-4">
          <!-- Error Message -->
          <div
            v-if="errorMessage"
            class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm"
          >
            {{ errorMessage }}
          </div>

          <!-- Input Mode Toggle -->
          <div class="flex rounded-lg border border-gray-200 overflow-hidden">
            <button
              type="button"
              @click="inputMode = 'number'"
              :class="[
                'flex-1 py-2 text-sm font-medium transition-colors',
                inputMode === 'number'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100',
              ]"
            >
              Tracking Number
            </button>
            <button
              type="button"
              @click="inputMode = 'url'"
              :class="[
                'flex-1 py-2 text-sm font-medium transition-colors',
                inputMode === 'url'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100',
              ]"
            >
              Direct URL
            </button>
          </div>

          <!-- Tracking Number Input -->
          <div v-if="inputMode === 'number'" class="flex flex-col gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Tracking Number *
              </label>
              <input
                v-model="form.tracking_number"
                type="text"
                placeholder="e.g., 1Z999AA10123456784"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <p class="mt-1 text-xs text-gray-500">
                Carrier will be auto-detected from the number format
              </p>
            </div>

            <!-- Optional Carrier Override -->
            <div v-if="showCarrierField">
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Carrier (optional)
              </label>
              <select
                v-model="form.tracking_carrier"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Auto-detect</option>
                <option v-for="carrier in carriers" :key="carrier" :value="carrier">
                  {{ carrier }}
                </option>
              </select>
              <p class="mt-1 text-xs text-gray-500">Override if auto-detection fails</p>
            </div>
          </div>

          <!-- Direct URL Input -->
          <div v-if="inputMode === 'url'">
            <label class="block text-sm font-medium text-gray-700 mb-1"> Tracking URL * </label>
            <input
              v-model="form.tracking_url"
              type="url"
              placeholder="https://..."
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="mt-1 text-xs text-gray-500">Paste a direct tracking link from any carrier</p>
          </div>

          <!-- Footer Buttons -->
          <div class="flex gap-3 pt-4">
            <button
              type="button"
              @click="handleClose"
              :disabled="submitting"
              class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="submitting"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ submitting ? "Adding..." : "Add Tracking" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
