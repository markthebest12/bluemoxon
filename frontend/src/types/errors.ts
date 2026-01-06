/**
 * Type definitions and guards for error handling.
 */

/**
 * Shape of axios-style errors with response data.
 */
export interface AxiosLikeError {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

/**
 * Type guard to check if an unknown error is an axios-like error.
 * Validates at runtime rather than using unsafe type assertions.
 */
export function isAxiosLikeError(e: unknown): e is AxiosLikeError {
  return typeof e === "object" && e !== null && ("response" in e || "message" in e);
}

/**
 * Extract error message from unknown error, handling axios-style errors.
 * @param e - The caught error
 * @param fallback - Default message if error cannot be parsed
 * @returns The extracted error message
 */
export function getErrorMessage(e: unknown, fallback = "An error occurred"): string {
  if (isAxiosLikeError(e)) {
    return e.response?.data?.detail || e.message || fallback;
  }
  if (e instanceof Error) {
    return e.message;
  }
  return fallback;
}
