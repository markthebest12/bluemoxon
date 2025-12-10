<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { useAcquisitionsStore, type AcquirePayload } from "@/stores/acquisitions";

const props = defineProps<{
  bookId: number;
  bookTitle: string;
  valueMid?: number;
}>();

const emit = defineEmits<{
  close: [];
  acquired: [];
}>();

const acquisitionsStore = useAcquisitionsStore();

const form = ref<AcquirePayload>({
  purchase_price: 0,
  purchase_date: new Date().toISOString().split("T")[0],
  order_number: "",
  place_of_purchase: "eBay",
  estimated_delivery: undefined,
});

const submitting = ref(false);
const errorMessage = ref<string | null>(null);

const estimatedDiscount = computed(() => {
  if (!props.valueMid || !form.value.purchase_price) return null;
  const discount = ((props.valueMid - form.value.purchase_price) / props.valueMid) * 100;
  return discount.toFixed(1);
});

// Lock body scroll when modal is open
watch(
  () => true, // Modal is always visible when component exists
  () => {
    document.body.style.overflow = "hidden";
  },
  { immediate: true }
);

// Clean up on unmount
onUnmounted(() => {
  document.body.style.overflow = "";
});

async function handleSubmit() {
  if (!form.value.purchase_price || !form.value.order_number) {
    errorMessage.value = "Please fill in all required fields";
    return;
  }

  submitting.value = true;
  errorMessage.value = null;

  try {
    await acquisitionsStore.acquireBook(props.bookId, form.value);
    emit("acquired");
    emit("close");
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to acquire book";
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
    <Transition name="fade">
      <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="handleClose"
      >
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
          <!-- Header -->
          <div class="flex items-center justify-between p-4 border-b border-gray-200">
            <div>
              <h2 class="text-lg font-semibold text-gray-900">Acquire Book</h2>
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
          <form @submit.prevent="handleSubmit" class="p-4 space-y-4">
            <!-- Error Message -->
            <div v-if="errorMessage" class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm">
              {{ errorMessage }}
            </div>

            <!-- Purchase Price -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Purchase Price *
              </label>
              <div class="relative">
                <span class="absolute left-3 top-2 text-gray-500">$</span>
                <input
                  v-model.number="form.purchase_price"
                  type="number"
                  step="0.01"
                  min="0"
                  class="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
              <p v-if="estimatedDiscount" class="mt-1 text-sm text-green-600">
                {{ estimatedDiscount }}% discount from FMV (${{ valueMid?.toFixed(2) }})
              </p>
            </div>

            <!-- Purchase Date -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Purchase Date *
              </label>
              <input
                v-model="form.purchase_date"
                type="date"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <!-- Order Number -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Order Number *
              </label>
              <input
                v-model="form.order_number"
                type="text"
                placeholder="19-13940-40744"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <!-- Platform -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Platform *
              </label>
              <select
                v-model="form.place_of_purchase"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="eBay">eBay</option>
                <option value="Etsy">Etsy</option>
                <option value="AbeBooks">AbeBooks</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <!-- Estimated Delivery -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Estimated Delivery
              </label>
              <input
                v-model="form.estimated_delivery"
                type="date"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
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
                {{ submitting ? "Processing..." : "Confirm Acquire" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
