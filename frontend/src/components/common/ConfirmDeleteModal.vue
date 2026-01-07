<script setup lang="ts">
withDefaults(
  defineProps<{
    visible: boolean;
    title: string;
    message: string;
    warningText: string;
    confirmButtonText: string;
    loading?: boolean;
    error?: string | null;
  }>(),
  {
    loading: false,
    error: null,
  }
);

const emit = defineEmits<{
  close: [];
  confirm: [];
}>();

function handleClose() {
  emit("close");
}

function handleConfirm() {
  emit("confirm");
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/50" @click="handleClose"></div>

      <!-- Modal -->
      <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 class="text-xl font-semibold text-gray-800 mb-4">{{ title }}</h3>

        <div class="mb-6">
          <p class="text-gray-600 mb-3">{{ message }}</p>
          <!-- Slot for custom content (e.g., image preview) -->
          <slot></slot>
          <p class="text-sm text-[var(--color-status-error-accent)] mt-3">
            {{ warningText }}
          </p>
        </div>

        <div
          v-if="error"
          class="mb-4 p-3 bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] rounded-sm text-[var(--color-status-error-text)] text-sm"
        >
          {{ error }}
        </div>

        <div class="flex justify-end gap-3">
          <button :disabled="loading" class="btn-secondary" @click="handleClose">Cancel</button>
          <button :disabled="loading" class="btn-danger" @click="handleConfirm">
            {{ loading ? "Deleting..." : confirmButtonText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
