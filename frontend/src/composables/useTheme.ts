import { ref, computed, watch } from "vue";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "theme";

function getStoredPreference(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
}

function getSystemPreference(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// ============================================
// SINGLETON STATE - shared across all instances
// ============================================
const preference = ref<ThemePreference>(getStoredPreference());
const systemPreference = ref<ResolvedTheme>(getSystemPreference());

const resolvedTheme = computed<ResolvedTheme>(() => {
  if (preference.value === "system") {
    return systemPreference.value;
  }
  return preference.value;
});

const isDark = computed(() => resolvedTheme.value === "dark");

// ============================================
// SINGLETON EFFECTS - run once at module load
// ============================================

// Apply theme to DOM and persist (single watcher, not per-component)
watch(
  resolvedTheme,
  (theme) => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(STORAGE_KEY, preference.value);
  },
  { immediate: true }
);

// Listen for system preference changes (single listener, not per-component)
if (typeof window !== "undefined") {
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  mediaQuery.addEventListener("change", (e: MediaQueryListEvent) => {
    systemPreference.value = e.matches ? "dark" : "light";
  });
}

// ============================================
// COMPOSABLE - just returns shared state
// ============================================
export function useTheme() {
  function toggle(): void {
    preference.value = isDark.value ? "light" : "dark";
  }

  function setTheme(theme: ThemePreference): void {
    preference.value = theme;
  }

  return {
    preference,
    resolvedTheme,
    isDark,
    toggle,
    setTheme,
  };
}
