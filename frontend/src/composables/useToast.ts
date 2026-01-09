import { ref, type Ref } from "vue";

export interface Toast {
  id: number;
  type: "error" | "success" | "warning";
  message: string;
  timestamp: number;
}

interface TimerState {
  timeoutId: ReturnType<typeof setTimeout>;
  remainingMs: number;
  startedAt: number;
}

const MAX_TOASTS = 3;
const AUTO_DISMISS_MS = 5000;
const DUPLICATE_SUPPRESSION_MS = 2000;

// Singleton state - shared across all useToast() calls
const toasts = ref<Toast[]>([]);
const timers = new Map<number, TimerState>();

// Incrementing counter for unique IDs (no collision possible)
let nextId = 1;

function isDuplicate(message: string): boolean {
  const now = Date.now();
  return toasts.value.some(
    (t) => t.message === message && now - t.timestamp < DUPLICATE_SUPPRESSION_MS
  );
}

function showError(message: string): void {
  addToast("error", message);
}

function showSuccess(message: string): void {
  addToast("success", message);
}

function showWarning(message: string): void {
  addToast("warning", message);
}

function addToast(type: "error" | "success" | "warning", message: string): void {
  // Suppress duplicates within the suppression window
  if (isDuplicate(message)) {
    return;
  }

  const id = nextId++;
  const toast: Toast = {
    id,
    type,
    message,
    timestamp: Date.now(),
  };

  toasts.value.push(toast);

  // Enforce max toasts limit - clear timers for shifted toasts
  while (toasts.value.length > MAX_TOASTS) {
    const removed = toasts.value.shift();
    if (removed) {
      clearTimerState(removed.id);
    }
  }

  // Auto-dismiss after timeout
  startTimer(id, AUTO_DISMISS_MS);
}

function startTimer(id: number, durationMs: number): void {
  const timeoutId = setTimeout(() => {
    dismiss(id);
  }, durationMs);

  timers.set(id, {
    timeoutId,
    remainingMs: durationMs,
    startedAt: Date.now(),
  });
}

function clearTimerState(id: number): void {
  const state = timers.get(id);
  if (state) {
    clearTimeout(state.timeoutId);
    timers.delete(id);
  }
}

function pauseTimer(id: number): void {
  const state = timers.get(id);
  if (state) {
    clearTimeout(state.timeoutId);
    const elapsed = Date.now() - state.startedAt;
    state.remainingMs = Math.max(0, state.remainingMs - elapsed);
  }
}

function resumeTimer(id: number): void {
  const state = timers.get(id);
  if (state && state.remainingMs > 0) {
    const timeoutId = setTimeout(() => {
      dismiss(id);
    }, state.remainingMs);
    state.timeoutId = timeoutId;
    state.startedAt = Date.now();
  }
}

function dismiss(id: number): void {
  clearTimerState(id);
  toasts.value = toasts.value.filter((t) => t.id !== id);
}

/** Reset all toasts and timers - for testing only */
function _reset(): void {
  toasts.value.forEach((t) => clearTimerState(t.id));
  toasts.value = [];
  nextId = 1;
}

// Base return type (always available)
interface UseToastReturn {
  toasts: Readonly<Ref<Toast[]>>;
  showError: (message: string) => void;
  showSuccess: (message: string) => void;
  showWarning: (message: string) => void;
  dismiss: (id: number) => void;
  pauseTimer: (id: number) => void;
  resumeTimer: (id: number) => void;
}

// Extended return type with _reset (dev only)
interface UseToastReturnDev extends UseToastReturn {
  _reset: () => void;
}

export function useToast(): UseToastReturn | UseToastReturnDev {
  const base: UseToastReturn = {
    toasts: toasts as Readonly<Ref<Toast[]>>,
    showError,
    showSuccess,
    showWarning,
    dismiss,
    pauseTimer,
    resumeTimer,
  };

  if (import.meta.env.DEV) {
    return {
      ...base,
      _reset,
    };
  }

  return base;
}
