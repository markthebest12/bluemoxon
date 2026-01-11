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
 * Publisher tier constants for type-safe comparisons.
 */
export const PUBLISHER_TIERS = {
  TIER_1: "TIER_1",
  TIER_2: "TIER_2",
  TIER_3: "TIER_3",
  TIER_4: "TIER_4",
} as const;

export type PublisherTier = (typeof PUBLISHER_TIERS)[keyof typeof PUBLISHER_TIERS];

/**
 * Publisher tier dropdown options with display labels.
 */
export const PUBLISHER_TIER_OPTIONS = [
  { value: "TIER_1", label: "Tier 1" },
  { value: "TIER_2", label: "Tier 2" },
  { value: "TIER_3", label: "Tier 3" },
  { value: "TIER_4", label: "Tier 4" },
] as const;

export type PublisherTierOption = (typeof PUBLISHER_TIER_OPTIONS)[number];

/**
 * Historical era constants for filtering.
 * Must match backend Era enum in app/enums.py
 */
export const BOOK_ERAS = {
  PRE_ROMANTIC: "Pre-Romantic",
  ROMANTIC: "Romantic",
  VICTORIAN: "Victorian",
  EDWARDIAN: "Edwardian",
  POST_1910: "Post-1910",
  UNKNOWN: "Unknown",
} as const;

export type BookEra = (typeof BOOK_ERAS)[keyof typeof BOOK_ERAS];

/**
 * Era filter options with display labels.
 * Values must match backend Era enum exactly.
 */
export const BOOK_ERA_OPTIONS = [
  { value: "Pre-Romantic", label: "Pre-Romantic (before 1800)" },
  { value: "Romantic", label: "Romantic (1800-1836)" },
  { value: "Victorian", label: "Victorian (1837-1901)" },
  { value: "Edwardian", label: "Edwardian (1902-1910)" },
  { value: "Post-1910", label: "Post-1910" },
  { value: "Unknown", label: "Unknown (no date)" },
] as const;

export type BookEraOption = (typeof BOOK_ERA_OPTIONS)[number];

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
