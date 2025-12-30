<script setup lang="ts">
import { ref, computed, watch } from "vue";
import TransitionModal from "@/components/TransitionModal.vue";
import type { EntityTier } from "@/types/admin";

const props = defineProps<{
  visible: boolean;
  entity: EntityTier | null;
  allEntities: EntityTier[];
  entityLabel: string;
  processing: boolean;
  error?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  "delete-direct": [];
  "reassign-delete": [targetId: number];
}>();

const selectedTargetId = ref<number | null>(null);
const confirmDelete = ref(false);

// Available targets (exclude self)
const targetOptions = computed(() => {
  if (!props.entity) return [];
  return props.allEntities.filter((e) => e.id !== props.entity!.id);
});

const hasBooks = computed(() => !!(props.entity && props.entity.book_count > 0));

// Reset selection when modal opens
watch(
  () => props.visible,
  (isVisible) => {
    if (isVisible) {
      selectedTargetId.value = null;
      confirmDelete.value = false;
    }
  }
);

function handleDelete() {
  if (hasBooks.value && selectedTargetId.value) {
    emit("reassign-delete", selectedTargetId.value);
  } else if (!hasBooks.value) {
    if (!confirmDelete.value) {
      confirmDelete.value = true;
      return;
    }
    emit("delete-direct");
  }
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="emit('close')">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 overflow-hidden">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h2 class="text-lg font-semibold text-gray-900">Delete {{ entityLabel }}</h2>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="px-6 py-4">
        <!-- Error -->
        <div
          v-if="error"
          class="mb-4 p-3 bg-[var(--color-status-error-bg)] text-[var(--color-status-error-text)] rounded text-sm"
        >
          {{ error }}
        </div>

        <div v-if="entity">
          <!-- Entity info -->
          <div class="mb-4">
            <p class="text-gray-900 font-medium">{{ entity.name }}</p>
            <p class="text-sm text-gray-500">
              {{ entity.book_count }} associated book{{ entity.book_count !== 1 ? "s" : "" }}
            </p>
          </div>

          <!-- No books - simple delete -->
          <div v-if="!hasBooks" class="p-4 bg-yellow-50 rounded">
            <p class="text-sm text-yellow-800">
              This {{ entityLabel.toLowerCase() }} has no books. It will be permanently deleted.
            </p>
          </div>

          <!-- Has books - must reassign -->
          <div v-else class="flex flex-col gap-4">
            <div class="p-4 bg-amber-50 rounded">
              <p class="text-sm text-amber-800">
                This {{ entityLabel.toLowerCase() }} has {{ entity.book_count }} book{{
                  entity.book_count !== 1 ? "s" : ""
                }}. Select a target to reassign them before deletion.
              </p>
            </div>

            <label class="block">
              <span class="text-sm font-medium text-gray-700"> Reassign books to * </span>
              <select
                v-model="selectedTargetId"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-gray-900 focus:ring-victorian-hunter-500 focus:border-victorian-hunter-500"
              >
                <option :value="null" disabled>
                  Select target {{ entityLabel.toLowerCase() }}
                </option>
                <option v-for="target in targetOptions" :key="target.id" :value="target.id">
                  {{ target.name }} ({{ target.book_count }} books)
                </option>
              </select>
            </label>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3 bg-gray-50">
        <button
          type="button"
          @click="emit('close')"
          class="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded transition-colors"
        >
          Cancel
        </button>
        <button
          @click="handleDelete"
          :disabled="processing || (hasBooks && !selectedTargetId)"
          class="px-4 py-2 text-sm text-white rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          :class="
            confirmDelete
              ? 'bg-[var(--color-status-error-solid)] hover:opacity-90'
              : 'bg-[var(--color-status-error-accent)] hover:opacity-90'
          "
        >
          {{
            processing
              ? "Processing..."
              : hasBooks
                ? "Reassign & Delete"
                : confirmDelete
                  ? "Click again to confirm"
                  : "Delete"
          }}
        </button>
      </div>
    </div>
  </TransitionModal>
</template>
