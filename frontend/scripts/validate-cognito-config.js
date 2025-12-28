#!/usr/bin/env node
/**
 * Validates Cognito configuration before production builds.
 *
 * This script prevents deploying frontend builds with incorrect Cognito settings,
 * which causes authentication failures that are difficult to diagnose.
 *
 * Usage:
 *   node scripts/validate-cognito-config.js [staging|prod]
 *
 * The script:
 * 1. Reads expected values from infra/config/{env}.json
 * 2. Compares against VITE_COGNITO_* environment variables
 * 3. Fails the build if there's a mismatch
 *
 * @see https://github.com/bluemoxon/bluemoxon/issues/474
 */

import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "..", "..");

// Determine environment from argument or VITE_API_URL
const args = process.argv.slice(2);
let environment = args[0];

if (!environment) {
  const apiUrl = process.env.VITE_API_URL || "";
  if (apiUrl.includes("staging")) {
    environment = "staging";
  } else if (apiUrl.includes("api.bluemoxon.com") && !apiUrl.includes("staging")) {
    environment = "prod";
  }
}

// Skip validation for local development
if (!environment) {
  console.log("Cognito validation: Skipping (local development - no environment detected)");
  process.exit(0);
}

console.log(`Cognito validation: Checking ${environment} configuration...`);

// Read expected config from infra/config/{env}.json
const configPath = join(projectRoot, "infra", "config", `${environment}.json`);
let expectedConfig;

try {
  const configContent = readFileSync(configPath, "utf-8");
  expectedConfig = JSON.parse(configContent);
} catch (error) {
  console.error(`ERROR: Could not read config file: ${configPath}`);
  console.error(error.message);
  process.exit(1);
}

// Extract expected Cognito values
const expected = {
  userPoolId: expectedConfig.cognito?.user_pool_id,
  appClientId: expectedConfig.cognito?.app_client_id,
  domain: expectedConfig.cognito?.domain,
};

// Get actual values from environment
const actual = {
  userPoolId: process.env.VITE_COGNITO_USER_POOL_ID || "",
  appClientId: process.env.VITE_COGNITO_APP_CLIENT_ID || "",
  domain: process.env.VITE_COGNITO_DOMAIN || "",
};

// Check for mismatches
const errors = [];

if (!actual.userPoolId) {
  errors.push(`VITE_COGNITO_USER_POOL_ID is not set (expected: ${expected.userPoolId})`);
} else if (actual.userPoolId !== expected.userPoolId) {
  errors.push(
    `VITE_COGNITO_USER_POOL_ID mismatch:\n` +
      `  Expected: ${expected.userPoolId}\n` +
      `  Actual:   ${actual.userPoolId}`
  );
}

if (!actual.appClientId) {
  errors.push(`VITE_COGNITO_APP_CLIENT_ID is not set (expected: ${expected.appClientId})`);
} else if (actual.appClientId !== expected.appClientId) {
  errors.push(
    `VITE_COGNITO_APP_CLIENT_ID mismatch:\n` +
      `  Expected: ${expected.appClientId}\n` +
      `  Actual:   ${actual.appClientId}`
  );
}

// Domain is optional for validation but good to check
if (actual.domain && expected.domain && actual.domain !== expected.domain) {
  console.warn(
    `WARNING: VITE_COGNITO_DOMAIN differs from config:\n` +
      `  Expected: ${expected.domain}\n` +
      `  Actual:   ${actual.domain}`
  );
}

// Report results
if (errors.length > 0) {
  console.error("\n" + "=".repeat(70));
  console.error("COGNITO CONFIGURATION ERROR - BUILD BLOCKED");
  console.error("=".repeat(70));
  console.error("\nThe following Cognito configuration issues were detected:\n");
  errors.forEach((err, i) => console.error(`${i + 1}. ${err}\n`));
  console.error("=".repeat(70));
  console.error("\nThis build was blocked to prevent authentication failures.");
  console.error("\nTo fix this issue:");
  console.error("  1. DO NOT deploy frontend locally - use CI/CD pipeline instead");
  console.error("  2. If you must build locally, ensure environment variables match:");
  console.error(`     VITE_COGNITO_USER_POOL_ID=${expected.userPoolId}`);
  console.error(`     VITE_COGNITO_APP_CLIENT_ID=${expected.appClientId}`);
  console.error(`     VITE_COGNITO_DOMAIN=${expected.domain}`);
  console.error("\nSee: https://github.com/bluemoxon/bluemoxon/issues/474");
  console.error("=".repeat(70) + "\n");
  process.exit(1);
}

console.log(`Cognito validation: PASSED (${environment})`);
console.log(`  User Pool ID: ${actual.userPoolId}`);
console.log(`  App Client ID: ${actual.appClientId}`);
process.exit(0);
