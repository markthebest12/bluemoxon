/**
 * Formatting utilities for display values.
 */

const ANALYSIS_ISSUE_LABELS: Record<string, string> = {
  truncated: "Truncated: recommendations section missing",
  degraded: "Degraded: fallback extraction used",
  missing_condition: "Missing: condition assessment",
  missing_market: "Missing: market analysis",
};

/**
 * Format analysis issues into a human-readable tooltip string.
 */
export function formatAnalysisIssues(issues: string[] | null | undefined): string {
  if (!issues || issues.length === 0) return "";
  return issues.map((i) => ANALYSIS_ISSUE_LABELS[i] || i).join("\n");
}
