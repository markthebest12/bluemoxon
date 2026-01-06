import { ref, type Ref } from "vue";

export interface Toast {
  id: number;
  type: "error" | "success";
  message: string;
  timestamp: number;
}

const MAX_TOASTS = 3;
const AUTO_DISMISS_MS = 5000;

// Singleton state - shared across all useToast() calls
const toasts = ref<Toast[]>([]);

function showError(message: string): void {
  addToast("error", message);
}

function showSuccess(message: string): void {
  addToast("success", message);
}

function addToast(type: "error" | "success", message: string): void {
  const id = Date.now() + Math.random();
  const toast: Toast = {
    id,
    type,
    message,
    timestamp: Date.now(),
  };

  toasts.value.push(toast);

  // Enforce max toasts limit
  while (toasts.value.length > MAX_TOASTS) {
    toasts.value.shift();
  }

  // Auto-dismiss after timeout
  setTimeout(() => {
    dismiss(id);
  }, AUTO_DISMISS_MS);
}

function dismiss(id: number): void {
  toasts.value = toasts.value.filter((t) => t.id !== id);
}

/** Reset all toasts - for testing only */
function _reset(): void {
  toasts.value = [];
}

export function useToast() {
  return {
    toasts: toasts as Readonly<Ref<Toast[]>>,
    showError,
    showSuccess,
    dismiss,
    _reset,
  };
}
