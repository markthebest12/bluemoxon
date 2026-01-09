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

/**
 * Condition grade constants for type-safe comparisons.
 */
export const CONDITION_GRADES = {
  FINE: "FINE",
  NEAR_FINE: "NEAR_FINE",
  VERY_GOOD: "VERY_GOOD",
  GOOD: "GOOD",
  FAIR: "FAIR",
  POOR: "POOR",
} as const;

export type ConditionGrade = (typeof CONDITION_GRADES)[keyof typeof CONDITION_GRADES];

/**
 * Condition grade dropdown options with display labels and descriptions.
 * Uses ABAA (Antiquarian Booksellers' Association of America) grading terminology.
 */
export const CONDITION_GRADE_OPTIONS = [
  { value: "FINE", label: "Fine", description: "Nearly as new, no defects" },
  { value: "NEAR_FINE", label: "Near Fine", description: "Approaching fine, very minor defects" },
  {
    value: "VERY_GOOD",
    label: "Very Good",
    description: "Worn but untorn, minimum for collectors",
  },
  { value: "GOOD", label: "Good", description: "Average used, regular wear" },
  { value: "FAIR", label: "Fair", description: "Wear and tear, but complete" },
  { value: "POOR", label: "Poor", description: "Heavily damaged, reading copy only" },
] as const;

export type ConditionGradeOption = (typeof CONDITION_GRADE_OPTIONS)[number];

/**
 * Book category constants.
 * Victorian-era book classification categories.
 */
export const BOOK_CATEGORIES = [
  "Victorian Poetry",
  "Victorian Literature",
  "Victorian Biography",
  "Romantic Poetry",
  "Romantic Literature",
  "Reference",
  "History",
  "Education",
  "Literature",
] as const;

export type BookCategory = (typeof BOOK_CATEGORIES)[number];
