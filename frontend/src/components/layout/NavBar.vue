<script setup lang="ts">
import { ref, computed } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import ThemeToggle from "@/components/ui/ThemeToggle.vue";

const router = useRouter();
const authStore = useAuthStore();
const showDropdown = ref(false);
const mobileMenuOpen = ref(false);

// Show first name if available, otherwise fall back to email
const displayName = computed(() => {
  if (authStore.user?.first_name) {
    return authStore.user.first_name;
  }
  return authStore.user?.email || "";
});

async function handleSignOut() {
  showDropdown.value = false;
  mobileMenuOpen.value = false;
  await authStore.logout();
  void router.push("/login");
}

function closeDropdown() {
  showDropdown.value = false;
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value;
}

function closeMobileMenu() {
  mobileMenuOpen.value = false;
}
</script>

<template>
  <nav
    class="bg-victorian-hunter-900 text-white shadow-lg sticky z-50"
    style="top: env(safe-area-inset-top, 0px)"
  >
    <div class="container mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <RouterLink to="/" class="flex items-center">
          <img src="/bluemoxon-classic-logo.png" alt="BlueMoxon" class="!h-14 w-auto" />
        </RouterLink>

        <!-- Desktop Navigation Links -->
        <div class="hidden md:flex items-center gap-6">
          <RouterLink
            to="/"
            class="text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors"
            active-class="text-victorian-gold-light"
          >
            Dashboard
          </RouterLink>
          <RouterLink
            to="/books"
            class="text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors"
            active-class="text-victorian-gold-light"
          >
            Collection
          </RouterLink>
          <RouterLink
            to="/reports/insurance"
            class="text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors"
            active-class="text-victorian-gold-light"
          >
            Reports
          </RouterLink>
          <RouterLink
            v-if="authStore.isAdmin"
            to="/admin/acquisitions"
            class="text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors"
            active-class="text-victorian-gold-light"
          >
            Acquisitions
          </RouterLink>
        </div>

        <!-- Right side: User Menu (desktop) + Hamburger (mobile) -->
        <div class="flex items-center gap-4">
          <!-- Theme Toggle - Desktop -->
          <div class="hidden md:block">
            <ThemeToggle />
          </div>
          <!-- User Menu - Desktop -->
          <div class="hidden md:flex items-center">
            <template v-if="authStore.isAuthenticated">
              <div class="relative">
                <button
                  @click="showDropdown = !showDropdown"
                  class="text-sm text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors flex items-center gap-1"
                  :title="authStore.user?.email"
                >
                  {{ displayName }}
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
                <!-- Dropdown Menu -->
                <Transition
                  enter-from-class="dropdown-enter-from"
                  enter-active-class="dropdown-enter-active"
                  leave-to-class="dropdown-leave-to"
                  leave-active-class="dropdown-leave-active"
                >
                  <div
                    v-if="showDropdown"
                    class="absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 z-50"
                    style="background-color: var(--color-surface-elevated)"
                    @click="closeDropdown"
                  >
                    <RouterLink
                      to="/profile"
                      class="block px-4 py-2 text-sm hover:bg-black/10 dark:hover:bg-white/10"
                      style="color: var(--color-text-primary)"
                    >
                      Profile
                    </RouterLink>
                    <RouterLink
                      v-if="authStore.isEditor"
                      to="/admin/config"
                      class="block px-4 py-2 text-sm hover:bg-black/10 dark:hover:bg-white/10"
                      style="color: var(--color-text-primary)"
                    >
                      Config
                    </RouterLink>
                    <RouterLink
                      v-if="authStore.isAdmin"
                      to="/admin"
                      class="block px-4 py-2 text-sm hover:bg-black/10 dark:hover:bg-white/10"
                      style="color: var(--color-text-primary)"
                    >
                      Admin Settings
                    </RouterLink>
                    <button
                      @click="handleSignOut"
                      class="block w-full text-left px-4 py-2 text-sm hover:bg-black/10 dark:hover:bg-white/10"
                      style="color: var(--color-text-primary)"
                    >
                      Sign Out
                    </button>
                  </div>
                </Transition>
              </div>
              <!-- Click outside to close -->
              <div v-if="showDropdown" class="fixed inset-0 z-40" @click="closeDropdown"></div>
            </template>
            <template v-else>
              <RouterLink
                to="/login"
                class="text-sm text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors"
              >
                Sign In
              </RouterLink>
            </template>
          </div>

          <!-- Theme Toggle - Mobile -->
          <div class="md:hidden">
            <ThemeToggle />
          </div>
          <!-- Hamburger Menu Button - Mobile -->
          <button
            @click="toggleMobileMenu"
            class="md:hidden flex flex-col justify-center items-center w-8 h-8 gap-1.5 focus:outline-none"
            aria-label="Toggle menu"
          >
            <span
              class="block w-6 h-0.5 bg-slate-200 transition-all duration-300"
              :class="{ 'rotate-45 translate-y-2': mobileMenuOpen }"
            ></span>
            <span
              class="block w-6 h-0.5 bg-slate-200 transition-all duration-300"
              :class="{ 'opacity-0': mobileMenuOpen }"
            ></span>
            <span
              class="block w-6 h-0.5 bg-slate-200 transition-all duration-300"
              :class="{ '-rotate-45 -translate-y-2': mobileMenuOpen }"
            ></span>
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile Menu -->
    <div
      v-if="mobileMenuOpen"
      class="md:hidden bg-victorian-hunter-900/98 border-t border-victorian-hunter-700"
    >
      <div class="px-4 py-3 flex flex-col gap-1">
        <!-- Navigation Links -->
        <RouterLink
          to="/"
          class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
          active-class="text-victorian-gold-light"
          @click="closeMobileMenu"
        >
          Dashboard
        </RouterLink>
        <RouterLink
          to="/books"
          class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
          active-class="text-victorian-gold-light"
          @click="closeMobileMenu"
        >
          Collection
        </RouterLink>
        <RouterLink
          to="/reports/insurance"
          class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
          active-class="text-victorian-gold-light"
          @click="closeMobileMenu"
        >
          Reports
        </RouterLink>
        <RouterLink
          v-if="authStore.isAdmin"
          to="/admin/acquisitions"
          class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
          active-class="text-victorian-gold-light"
          @click="closeMobileMenu"
        >
          Acquisitions
        </RouterLink>

        <!-- User Section -->
        <template v-if="authStore.isAuthenticated">
          <RouterLink
            to="/profile"
            class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
            @click="closeMobileMenu"
          >
            Profile
          </RouterLink>
          <RouterLink
            v-if="authStore.isEditor"
            to="/admin/config"
            class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
            @click="closeMobileMenu"
          >
            Config
          </RouterLink>
          <RouterLink
            v-if="authStore.isAdmin"
            to="/admin"
            class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
            @click="closeMobileMenu"
          >
            Admin Settings
          </RouterLink>
          <button
            @click="handleSignOut"
            class="block w-full text-left py-3 text-victorian-paper-cream/80 hover:text-victorian-burgundy-light"
          >
            Sign Out
          </button>
        </template>
        <template v-else>
          <RouterLink
            to="/login"
            class="block py-3 text-victorian-gold-light hover:text-victorian-gold"
            @click="closeMobileMenu"
          >
            Sign In
          </RouterLink>
        </template>
      </div>
    </div>

    <!-- Click outside to close mobile menu -->
    <div
      v-if="mobileMenuOpen"
      class="fixed inset-0 z-[-1] md:hidden"
      @click="closeMobileMenu"
    ></div>
  </nav>
</template>
