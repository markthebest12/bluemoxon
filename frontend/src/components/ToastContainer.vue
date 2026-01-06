<script setup lang="ts">
import { useToast } from "@/composables/useToast";

const { toasts, dismiss } = useToast();
</script>

<template>
  <div
    class="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
    aria-live="polite"
  >
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        role="alert"
        class="toast rounded-lg border px-4 py-3 shadow-lg flex items-start gap-3"
        :class="[
          toast.type === 'error' ? 'toast-error' : 'toast-success',
          toast.type === 'error'
            ? 'bg-[var(--color-status-error-bg)] border-[var(--color-status-error-border)] text-[var(--color-status-error-text)]'
            : 'bg-[var(--color-status-success-bg)] border-[var(--color-status-success-border)] text-[var(--color-status-success-text)]',
        ]"
      >
        <span
          class="flex-shrink-0 text-lg"
          :class="
            toast.type === 'error'
              ? 'text-[var(--color-status-error-accent)]'
              : 'text-[var(--color-status-success-accent)]'
          "
        >
          {{ toast.type === "error" ? "!" : "+" }}
        </span>
        <span class="flex-1 text-sm">{{ toast.message }}</span>
        <button
          type="button"
          aria-label="Dismiss notification"
          class="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
          @click="dismiss(toast.id)"
        >
          x
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.2s ease-in;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
