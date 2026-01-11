import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { fetchAuthSession } from "aws-amplify/auth";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";
const DEV_API_KEY = import.meta.env.VITE_API_KEY || "";

// Retry configuration
const MAX_RETRIES = 3;
const INITIAL_DELAY_MS = 1000; // 1 second
const MAX_DELAY_MS = 10000; // 10 seconds

// Extended config type to track retry count
interface RetryConfig extends InternalAxiosRequestConfig {
  __retryCount?: number;
}

// Check if error is retryable (network errors or 5xx server errors)
function isRetryableError(error: AxiosError): boolean {
  // Network errors (no response)
  if (!error.response) {
    return true;
  }
  // Server errors (5xx)
  const status = error.response.status;
  return status >= 500 && status < 600;
}

// Calculate delay with exponential backoff + jitter
function getRetryDelay(retryCount: number): number {
  const exponentialDelay = INITIAL_DELAY_MS * Math.pow(2, retryCount);
  const jitter = Math.random() * 1000; // Add 0-1s jitter
  return Math.min(exponentialDelay + jitter, MAX_DELAY_MS);
}

// Sleep helper
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30s timeout per request
});

// Add auth token to requests
api.interceptors.request.use(async (config) => {
  // Use API key bypass for local dev if configured
  if (DEV_API_KEY) {
    config.headers["X-API-Key"] = DEV_API_KEY;
    console.log("[API] Using API key auth (dev mode)");
    return config;
  }

  try {
    console.log(`[API] Request interceptor for ${config.method?.toUpperCase()} ${config.url}`);
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log("[API] Auth token added to request");
    } else {
      console.warn("[API] No auth token available");
    }
  } catch (e) {
    console.error("[API] Auth session error:", e);
  }
  return config;
});

// Handle auth errors and retries
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined;

    // Only redirect to login if not already on login page
    if (error.response?.status === 401 && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
      return Promise.reject(error);
    }

    // Handle retries for network/server errors
    if (config && isRetryableError(error)) {
      config.__retryCount = config.__retryCount ?? 0;

      if (config.__retryCount < MAX_RETRIES) {
        config.__retryCount += 1;
        const delay = getRetryDelay(config.__retryCount);
        console.log(
          `[API] Retry ${config.__retryCount}/${MAX_RETRIES} for ${config.url} after ${Math.round(delay)}ms`
        );
        await sleep(delay);
        return api.request(config);
      }

      console.warn(`[API] Max retries (${MAX_RETRIES}) exceeded for ${config.url}`);
    }

    return Promise.reject(error);
  }
);
