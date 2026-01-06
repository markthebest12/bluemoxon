/**
 * Centralized constants for the BlueMoxon frontend.
 * Extracted to eliminate duplication and magic numbers.
 */

/**
 * Book status string constants for type-safe comparisons.
 */
export const BOOK_STATUSES = {
  EVALUATING: "EVALUATING",
  ON_HAND: "ON_HAND",
  IN_TRANSIT: "IN_TRANSIT",
  REMOVED: "REMOVED",
} as const;

export type BookStatus = (typeof BOOK_STATUSES)[keyof typeof BOOK_STATUSES];

/**
 * Status dropdown options with display labels.
 * Values derived from BOOK_STATUSES for single source of truth.
 */
export const BOOK_STATUS_OPTIONS = [
  { value: BOOK_STATUSES.EVALUATING, label: "EVAL" },
  { value: BOOK_STATUSES.ON_HAND, label: "ON HAND" },
  { value: BOOK_STATUSES.IN_TRANSIT, label: "IN TRANSIT" },
  { value: BOOK_STATUSES.REMOVED, label: "REMOVED" },
] as const;

export type BookStatusOption = (typeof BOOK_STATUS_OPTIONS)[number];

/**
 * Pagination configuration constants.
 */
export const PAGINATION = {
  /** Default items per page for API calls */
  DEFAULT_PER_PAGE: 100,
  /** Items per page for received books list */
  RECEIVED_PER_PAGE: 50,
  /** Default items per page for books list */
  BOOKS_PER_PAGE: 20,
} as const;

/**
 * Filter/business rule constants.
 */
export const FILTERS = {
  /** Days to look back for received items */
  RECEIVED_DAYS_LOOKBACK: 30,
} as const;

/**
 * UI timing constants in milliseconds.
 */
export const UI_TIMING = {
  /** Delay before closing combobox dropdown on blur */
  COMBOBOX_BLUR_DELAY_MS: 200,
} as const;
