/**
 * Application configuration
 *
 * Version and build info are injected at build time by vite.config.ts
 */

// Build-time injected version info (full string includes +sha build metadata)
export const APP_VERSION = __APP_VERSION__;
// Semver only (strips +build metadata) for UI display
export const APP_VERSION_DISPLAY = APP_VERSION.split("+")[0];
export const BUILD_TIME = __BUILD_TIME__;

// Runtime config from environment variables
export const API_URL = import.meta.env.VITE_API_URL || "";

// Analysis model configuration
export type AnalysisModel = "sonnet" | "opus";
export const DEFAULT_ANALYSIS_MODEL: AnalysisModel = "opus";

// Cognito config
export const COGNITO_CONFIG = {
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || "",
  appClientId: import.meta.env.VITE_COGNITO_APP_CLIENT_ID || "",
  region: import.meta.env.VITE_COGNITO_REGION || "us-west-2",
};

/**
 * Get version info for display
 */
export function getVersionInfo() {
  return {
    version: APP_VERSION,
    buildTime: BUILD_TIME,
  };
}
