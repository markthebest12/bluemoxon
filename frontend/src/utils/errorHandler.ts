import { getErrorMessage } from "@/types/errors";
import { useToast } from "@/composables/useToast";

/**
 * Handle API errors by extracting message, logging, and showing toast.
 * Use in catch blocks for user-facing error feedback.
 *
 * @param error - The caught error
 * @param context - Description of what was being attempted (e.g., "Loading images")
 * @returns The extracted error message (for inline display if needed)
 */
export function handleApiError(error: unknown, context: string): string {
  const message = getErrorMessage(error, `Failed: ${context}`);
  console.error(`[${context}]`, message, error);

  const { showError } = useToast();
  showError(message);

  return message;
}

/**
 * Show success toast for completed actions.
 *
 * @param message - Success message to display
 */
export function handleSuccess(message: string): void {
  const { showSuccess } = useToast();
  showSuccess(message);
}
