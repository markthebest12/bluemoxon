import axios from "axios";
import { fetchAuthSession } from "aws-amplify/auth";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";
const DEV_API_KEY = import.meta.env.VITE_API_KEY || "";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
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

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect to login if not already on login page
    if (error.response?.status === 401 && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
