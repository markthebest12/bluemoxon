import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomeView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/books",
      name: "books",
      component: () => import("@/views/BooksView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/books/new",
      name: "book-create",
      component: () => import("@/views/BookCreateView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/books/:id",
      name: "book-detail",
      component: () => import("@/views/BookDetailView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/books/:id/edit",
      name: "book-edit",
      component: () => import("@/views/BookEditView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/search",
      name: "search",
      component: () => import("@/views/SearchView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      path: "/profile",
      name: "profile",
      component: () => import("@/views/ProfileView.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

// Navigation guard for authentication
let authInitialized = false;

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  // Initialize auth on first navigation
  if (!authInitialized) {
    await authStore.checkAuth();
    authInitialized = true;
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (to.name === "login" && authStore.isAuthenticated) {
    // Redirect to home if already logged in
    next({ name: "home" });
  } else {
    next();
  }
});

export default router;
