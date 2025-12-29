import { createApp } from "vue";
import { createPinia } from "pinia";
import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";

import App from "./App.vue";
import router from "./router";
import "./assets/main.css";
import { APP_VERSION } from "./config";

// Version from VERSION file at build time
console.log(`[BlueMoxon] App version: ${APP_VERSION}`);

// Disable browser's native scroll restoration - let Vue Router handle it
if ("scrollRestoration" in history) {
  history.scrollRestoration = "manual";
}

// Configure Amplify
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || "",
      userPoolClientId: import.meta.env.VITE_COGNITO_APP_CLIENT_ID || "",
    },
  },
});

// Pre-initialize Amplify auth session before app mounts
// This ensures tokens are loaded from localStorage before router guards run
async function initApp() {
  try {
    await fetchAuthSession();
    console.log("[BlueMoxon] Auth session initialized");
  } catch (_e) {
    console.log("[BlueMoxon] No existing auth session");
  }

  const app = createApp(App);
  app.use(createPinia());
  app.use(router);
  app.mount("#app");
}

void initApp();
