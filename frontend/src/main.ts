import { createApp } from "vue";
import { createPinia } from "pinia";
import { Amplify } from "aws-amplify";

import App from "./App.vue";
import router from "./router";
import "./assets/main.css";

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
