import { getErrorMessage } from "@/types/errors";
import { useToast } from "@/composables/useToast";

type ErrorCallback = (message: string) => void;
type SuccessCallback = (message: string) => void;

// Get default toast functions lazily to avoid import-time Vue dependency
function getDefaultShowError(): ErrorCallback {
  return useToast().showError;
}

function getDefaultShowSuccess(): SuccessCallback {
  return useToast().showSuccess;
}

/**
 * Handle API errors by extracting message, logging, and showing toast.
 * Use in catch blocks for user-facing error feedback.
 *
 * @param error - The caught error
 * @param context - Description of what was being attempted (e.g., "Loading images")
 * @param onError - Optional callback to show error (defaults to useToast().showError)
 * @returns The extracted error message (for inline display if needed)
 */
export function handleApiError(error: unknown, context: string, onError?: ErrorCallback): string {
  const message = getErrorMessage(error, `Failed: ${context}`);
  console.error(`[${context}]`, message, error);

  const showError = onError ?? getDefaultShowError();
  showError(message);

  return message;
}

/**
 * Show success toast for completed actions.
 *
 * @param message - Success message to display
 * @param onSuccess - Optional callback to show success (defaults to useToast().showSuccess)
 */
export function handleSuccess(message: string, onSuccess?: SuccessCallback): void {
  const showSuccess = onSuccess ?? getDefaultShowSuccess();
  showSuccess(message);
}
