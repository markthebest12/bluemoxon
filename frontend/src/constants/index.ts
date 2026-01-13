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

/**
 * Dashboard stat card definitions with tooltips.
 * Used for overview metrics on the dashboard.
 */
export const DASHBOARD_STAT_CARDS = {
  ON_HAND: {
    label: "On Hand",
    description: "Total number of books currently in your collection with ON_HAND status",
    filterParam: "status=ON_HAND",
  },
  VOLUMES: {
    label: "Volumes",
    description: "Total individual volumes across all books (multi-volume sets count each volume)",
    filterParam: "status=ON_HAND",
  },
  EST_VALUE: {
    label: "Est. Value",
    description: "Estimated mid-range market value of your ON_HAND collection",
    filterParam: "status=ON_HAND",
  },
  PREMIUM: {
    label: "Premium",
    description:
      "Books with authenticated premium bindings (Zaehnsdorf, Riviere, Sangorski & Sutcliffe, etc.)",
    filterParam: "binding_authenticated=true",
  },
} as const;

export type DashboardStatCard = keyof typeof DASHBOARD_STAT_CARDS;

/**
 * Era definitions with year ranges for tooltips.
 * Matches backend era classification in stats.py
 */
export const ERA_DEFINITIONS = {
  "Pre-Romantic (before 1800)": {
    label: "Pre-Romantic",
    years: "Before 1800",
    description: "Works published before the Romantic period",
  },
  "Romantic (1800-1836)": {
    label: "Romantic",
    years: "1800-1836",
    description: "The Romantic era, featuring Wordsworth, Coleridge, Byron, Shelley, Keats",
  },
  "Victorian (1837-1901)": {
    label: "Victorian",
    years: "1837-1901",
    description: "Queen Victoria's reign, the golden age of British publishing",
  },
  "Edwardian (1902-1910)": {
    label: "Edwardian",
    years: "1902-1910",
    description: "King Edward VII's reign, continuation of Victorian traditions",
  },
  "Post-1910": {
    label: "Post-1910",
    years: "After 1910",
    description: "Modern era, after the Edwardian period",
  },
  Unknown: {
    label: "Unknown",
    years: "No date",
    description: "Books without a recorded publication date",
  },
} as const;

export type EraDefinition = (typeof ERA_DEFINITIONS)[keyof typeof ERA_DEFINITIONS];
