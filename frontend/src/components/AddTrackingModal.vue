<script setup lang="ts">
import { ref, computed } from "vue";
import { useAcquisitionsStore, type TrackingPayload } from "@/stores/acquisitions";
import TransitionModal from "./TransitionModal.vue";

const props = defineProps<{
  visible: boolean;
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
  } catch (e: unknown) {
    let detail = "Failed to add tracking";
    if (e instanceof Error) {
      detail = e.message;
    }
    if (typeof e === "object" && e !== null && "response" in e) {
      const response = (e as { response?: { data?: { detail?: string } } }).response;
      if (response?.data?.detail) {
        detail = response.data.detail;
      }
    }
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
  <TransitionModal :visible="visible" @backdrop-click="handleClose">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b border-gray-200">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">Add Tracking</h2>
          <p class="text-sm text-gray-600 truncate">{{ bookTitle }}</p>
        </div>
        <button
          :disabled="submitting"
          class="text-gray-500 hover:text-gray-700 disabled:opacity-50"
          @click="handleClose"
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
      <form class="p-4 flex flex-col gap-4" @submit.prevent="handleSubmit">
        <!-- Error Message -->
        <div
          v-if="errorMessage"
          class="bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] text-[var(--color-status-error-text)] p-3 rounded-lg text-sm"
        >
          {{ errorMessage }}
        </div>

        <!-- Input Mode Toggle -->
        <div class="flex rounded-lg border border-gray-200 overflow-hidden">
          <button
            type="button"
            :class="[
              'flex-1 py-2 text-sm font-medium transition-colors',
              inputMode === 'number'
                ? 'bg-victorian-hunter-600 text-white'
                : 'bg-gray-50 text-gray-600 hover:bg-victorian-paper-aged',
            ]"
            @click="inputMode = 'number'"
          >
            Tracking Number
          </button>
          <button
            type="button"
            :class="[
              'flex-1 py-2 text-sm font-medium transition-colors',
              inputMode === 'url'
                ? 'bg-victorian-hunter-600 text-white'
                : 'bg-gray-50 text-gray-600 hover:bg-victorian-paper-aged',
            ]"
            @click="inputMode = 'url'"
          >
            Direct URL
          </button>
        </div>

        <!-- Tracking Number Input -->
        <div v-if="inputMode === 'number'" class="flex flex-col gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Tracking Number * </label>
            <input
              v-model="form.tracking_number"
              type="text"
              placeholder="e.g., 1Z999AA10123456784"
              class="input"
            />
            <p class="mt-1 text-xs text-gray-500">
              Carrier will be auto-detected from the number format
            </p>
          </div>

          <!-- Optional Carrier Override -->
          <div v-if="showCarrierField">
            <label class="block text-sm font-medium text-gray-700 mb-1"> Carrier (optional) </label>
            <select v-model="form.tracking_carrier" class="select">
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
          <input v-model="form.tracking_url" type="url" placeholder="https://..." class="input" />
          <p class="mt-1 text-xs text-gray-500">Paste a direct tracking link from any carrier</p>
        </div>

        <!-- Footer Buttons -->
        <div class="flex gap-3 pt-4">
          <button
            type="button"
            :disabled="submitting"
            class="btn-secondary flex-1"
            @click="handleClose"
          >
            Cancel
          </button>
          <button type="submit" :disabled="submitting" class="btn-primary flex-1">
            {{ submitting ? "Adding..." : "Add Tracking" }}
          </button>
        </div>
      </form>
    </div>
  </TransitionModal>
</template>
