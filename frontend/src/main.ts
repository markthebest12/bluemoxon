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

initApp().catch((error: unknown) => {
  console.error("App initialization failed:", error);
  const appEl = document.getElementById("app");
  if (appEl) {
    appEl.innerHTML = `
      <div style="padding: 40px; font-family: system-ui, sans-serif; text-align: center;">
        <h1 style="color: #7c2d12; margin-bottom: 16px;">Failed to load application</h1>
        <p style="color: #57534e;">Please refresh the page or contact support if the problem persists.</p>
      </div>
    `;
  }
});
