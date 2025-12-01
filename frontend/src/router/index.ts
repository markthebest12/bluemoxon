import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(_to, _from, savedPosition) {
    // If using browser back/forward, restore saved position
    if (savedPosition) {
      return savedPosition;
    }
    // Otherwise scroll to top with slight delay to ensure DOM is ready
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ top: 0, left: 0, behavior: "instant" });
      }, 0);
    });
  },
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
    {
      path: "/admin",
      name: "admin",
      component: () => import("@/views/AdminView.vue"),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
  ],
});

// Navigation guard for authentication
let authInitialized = false;

// Fallback scroll reset for browsers where scrollBehavior doesn't work (Chrome mobile)
router.afterEach((to) => {
  console.log(`[Router] afterEach: navigated to ${to.path}, scrolling to top`);
  // Use multiple approaches for maximum browser compatibility
  setTimeout(() => {
    // Method 1: Standard scrollTo
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    // Method 2: Direct property set (needed for some mobile browsers)
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    console.log("[Router] Scroll reset complete");
  }, 50); // Longer delay for mobile Chrome
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  // Initialize auth on first navigation
  if (!authInitialized) {
    await authStore.checkAuth();
    authInitialized = true;
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    // Admin-only routes redirect to home if not admin
    next({ name: "home" });
  } else if (to.name === "login" && authStore.isAuthenticated) {
    // Redirect to home if already logged in
    next({ name: "home" });
  } else {
    next();
  }
});

export default router;
