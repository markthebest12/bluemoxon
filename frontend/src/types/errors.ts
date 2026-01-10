/**
 * Type definitions and guards for error handling.
 */

/**
 * Pydantic validation error item from FastAPI.
 */
interface ValidationErrorItem {
  type: string;
  loc: (string | number)[];
  msg: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

/**
 * Shape of axios-style errors with response data.
 */
export interface AxiosLikeError {
  response?: {
    data?: {
      detail?: string | ValidationErrorItem[];
    };
  };
  message?: string;
}

/**
 * Type guard to check if an unknown error is an axios-like error.
 * Validates at runtime rather than using unsafe type assertions.
 */
export function isAxiosLikeError(e: unknown): e is AxiosLikeError {
  return typeof e === "object" && e !== null && "response" in e;
}

/**
 * Convert snake_case field name to human-readable Title Case.
 */
function formatFieldName(field: string): string {
  return field
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Format a Pydantic validation error into a human-readable message.
 */
function formatValidationError(error: ValidationErrorItem): string {
  // Get the field name (skip 'body' prefix)
  const fieldPath = error.loc.filter((part) => part !== "body");
  const fieldName = fieldPath.length > 0 ? formatFieldName(String(fieldPath[0])) : "Field";

  // Create human-readable message based on error type
  switch (error.type) {
    case "enum":
      if (error.ctx?.expected) {
        const expected = String(error.ctx.expected)
          .replace(/'/g, "")
          .split(", ")
          .map((v) => formatFieldName(v))
          .join(", ");
        return `${fieldName}: Please select a valid option (${expected})`;
      }
      return `${fieldName}: Invalid selection`;

    case "missing":
      return `${fieldName} is required`;

    case "string_type":
      return `${fieldName} must be text`;

    case "int_type":
    case "float_type":
      return `${fieldName} must be a number`;

    case "bool_type":
      return `${fieldName} must be yes or no`;

    case "value_error":
    case "assertion_error":
      return `${fieldName}: ${error.msg}`;

    default:
      // Fallback to the raw message, cleaned up
      return `${fieldName}: ${error.msg}`;
  }
}

/**
 * Check if detail is an array of Pydantic validation errors.
 */
function isValidationErrorArray(detail: unknown): detail is ValidationErrorItem[] {
  return (
    Array.isArray(detail) &&
    detail.length > 0 &&
    typeof detail[0] === "object" &&
    detail[0] !== null &&
    "loc" in detail[0] &&
    "msg" in detail[0]
  );
}

/**
 * Extract error message from unknown error, handling axios-style errors.
 * @param e - The caught error
 * @param fallback - Default message if error cannot be parsed
 * @returns The extracted error message
 */
export function getErrorMessage(e: unknown, fallback = "An error occurred"): string {
  if (isAxiosLikeError(e)) {
    const detail = e.response?.data?.detail;

    // Handle Pydantic validation errors (array of error objects)
    if (isValidationErrorArray(detail)) {
      const messages = detail.map(formatValidationError);
      return messages.join(". ");
    }

    // Handle string detail
    if (typeof detail === "string") {
      return detail;
    }

    return e instanceof Error ? e.message : fallback;
  }
  if (e instanceof Error) {
    return e.message;
  }
  return fallback;
}

/**
 * Extract HTTP status code from unknown error.
 * @param e - The caught error
 * @returns The HTTP status code, or undefined if not available
 */
export function getHttpStatus(e: unknown): number | undefined {
  if (typeof e === "object" && e !== null && "response" in e) {
    const response = (e as { response?: { status?: number } }).response;
    return response?.status;
  }
  return undefined;
}

/**
 * Entity suggestion from 409 conflict response.
 */
export interface EntitySuggestion {
  id: number;
  name: string;
  tier?: string;
  match: number;
  book_count: number;
}

/**
 * 409 Conflict response when creating similar entity.
 */
export interface EntityConflictResponse {
  error: "similar_entity_exists";
  entity_type: string;
  input: string;
  suggestions: EntitySuggestion[];
  resolution: string;
}

/**
 * Type guard for entity conflict response.
 */
export function isEntityConflictResponse(data: unknown): data is EntityConflictResponse {
  if (typeof data !== "object" || data === null) return false;
  const obj = data as Record<string, unknown>;
  return (
    obj.error === "similar_entity_exists" &&
    typeof obj.entity_type === "string" &&
    typeof obj.input === "string" &&
    Array.isArray(obj.suggestions)
  );
}
