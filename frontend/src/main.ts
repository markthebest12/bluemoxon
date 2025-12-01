import { createApp } from "vue";
import { createPinia } from "pinia";
import { Amplify } from "aws-amplify";

import App from "./App.vue";
import router from "./router";
import "./assets/main.css";

// Version for debugging - update this when making changes
const APP_VERSION = "2025-12-01-v3";
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

const app = createApp(App);

app.use(createPinia());
app.use(router);

app.mount("#app");
