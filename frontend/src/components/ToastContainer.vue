<script setup lang="ts">
import { useToast } from "@/composables/useToast";

const { toasts, dismiss, pauseTimer, resumeTimer } = useToast();
</script>

<template>
  <div class="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :role="toast.type === 'error' ? 'alert' : 'status'"
        class="toast rounded-lg border px-5 py-4 shadow-lg flex items-start gap-3"
        :class="[
          toast.type === 'error' ? 'toast-error' : 'toast-success',
          toast.type === 'error'
            ? 'bg-[var(--color-status-error-bg)] border-[var(--color-status-error-border)] text-[var(--color-status-error-text)]'
            : 'bg-[var(--color-status-success-bg)] border-[var(--color-status-success-border)] text-[var(--color-status-success-text)]',
        ]"
        @mouseenter="pauseTimer(toast.id)"
        @mouseleave="resumeTimer(toast.id)"
      >
        <span
          class="flex-shrink-0 text-xl font-bold"
          :class="
            toast.type === 'error'
              ? 'text-[var(--color-status-error-accent)]'
              : 'text-[var(--color-status-success-accent)]'
          "
        >
          {{ toast.type === "error" ? "\u2717" : "\u2713" }}
        </span>
        <span class="flex-1 text-sm">{{ toast.message }}</span>
        <button
          type="button"
          aria-label="Dismiss notification"
          class="flex-shrink-0 ml-2 w-6 h-6 flex items-center justify-center rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors font-bold text-lg"
          @click="dismiss(toast.id)"
        >
          ×
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

.toast-move {
  transition: transform 0.3s ease;
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
