<script setup lang="ts">
/**
 * SocialCirclesCard - Dashboard preview card for Victorian Social Circles.
 *
 * Lightweight preview with decorative SVG network visualization,
 * summary stats, and CTA to explore the full feature.
 */

import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/services/api";

interface SocialCirclesStats {
  total_authors: number;
  total_publishers: number;
  total_binders: number;
  total_books: number;
}

const router = useRouter();

// State
const stats = ref<SocialCirclesStats | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

// Fetch stats from the social circles API
async function fetchStats(): Promise<void> {
  loading.value = true;
  error.value = null;

  try {
    const response = await api.get("/social-circles/");
    // Extract meta from response
    const meta = response.data?.meta;
    if (meta) {
      stats.value = {
        total_authors: meta.total_authors || 0,
        total_publishers: meta.total_publishers || 0,
        total_binders: meta.total_binders || 0,
        total_books: meta.total_books || 0,
      };
    }
  } catch {
    // Fail silently - card just won't show stats
    error.value = "Unable to load network stats";
  } finally {
    loading.value = false;
  }
}

// Navigate to social circles view
function exploreNetwork(event?: MouseEvent): void {
  const url = "/social-circles";
  if (event?.metaKey || event?.ctrlKey) {
    window.open(url, "_blank");
  } else {
    void router.push(url);
  }
}

// Computed
const totalNodes = computed(() => {
  if (!stats.value) return 0;
  return stats.value.total_authors + stats.value.total_publishers + stats.value.total_binders;
});

const showContent = computed(() => !loading.value && !error.value && stats.value !== null);

onMounted(() => {
  void fetchStats();
});
</script>

<template>
  <div class="mt-8 md:mt-12">
    <!-- Section Header -->
    <div class="flex items-center gap-3 mb-4">
      <h2 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider">
        Literary Connections
      </h2>
      <div class="flex-1 h-px bg-victorian-paper-antique"></div>
    </div>

    <!-- Card -->
    <div
      class="card-static p-6 cursor-pointer hover:ring-2 hover:ring-victorian-hunter-600/30 transition-all"
      @click="exploreNetwork($event)"
    >
      <div class="flex flex-col md:flex-row gap-6 items-center">
        <!-- Decorative Network SVG -->
        <div class="w-32 h-32 md:w-40 md:h-40 flex-shrink-0">
          <svg viewBox="0 0 100 100" class="w-full h-full" aria-hidden="true">
            <!-- Background circle -->
            <circle cx="50" cy="50" r="45" fill="none" stroke="#e8e4d9" stroke-width="0.5" />

            <!-- Network edges -->
            <g stroke="#8fa89a" stroke-width="0.75" opacity="0.6">
              <line x1="50" y1="20" x2="25" y2="50" />
              <line x1="50" y1="20" x2="75" y2="50" />
              <line x1="25" y1="50" x2="50" y2="80" />
              <line x1="75" y1="50" x2="50" y2="80" />
              <line x1="25" y1="50" x2="75" y2="50" />
              <line x1="50" y1="20" x2="50" y2="80" />
              <line x1="20" y1="35" x2="50" y2="20" />
              <line x1="80" y1="35" x2="50" y2="20" />
              <line x1="20" y1="65" x2="25" y2="50" />
              <line x1="80" y1="65" x2="75" y2="50" />
            </g>

            <!-- Author nodes (circles) -->
            <circle cx="50" cy="20" r="6" fill="#254a3d" />
            <circle cx="20" cy="35" r="4" fill="#2f5a4b" />
            <circle cx="80" cy="35" r="4" fill="#2f5a4b" />

            <!-- Publisher nodes (diamonds) -->
            <g fill="#722f37">
              <polygon points="25,44 31,50 25,56 19,50" />
              <polygon points="75,44 81,50 75,56 69,50" />
            </g>

            <!-- Binder nodes (squares) -->
            <rect x="46" y="76" width="8" height="8" fill="#8b6914" />
            <rect x="16" y="61" width="6" height="6" fill="#a67c17" />
            <rect x="78" y="61" width="6" height="6" fill="#a67c17" />
          </svg>
        </div>

        <!-- Content -->
        <div class="flex-1 text-center md:text-left">
          <h3 class="text-xl font-display text-victorian-hunter-700 mb-2">
            Victorian Social Circles
          </h3>
          <p class="text-sm text-victorian-ink-muted mb-4 max-w-md">
            Explore the connections between authors, publishers, and binders in your collection.
            Discover literary networks and relationships from the Victorian era.
          </p>

          <!-- Stats -->
          <div v-if="showContent" class="flex flex-wrap gap-4 mb-4 justify-center md:justify-start">
            <div class="text-center">
              <span class="block text-lg font-display text-victorian-hunter-800">
                {{ stats?.total_authors || 0 }}
              </span>
              <span class="text-xs text-victorian-ink-muted uppercase tracking-wider">Authors</span>
            </div>
            <div class="text-center">
              <span class="block text-lg font-display text-victorian-burgundy">
                {{ stats?.total_publishers || 0 }}
              </span>
              <span class="text-xs text-victorian-ink-muted uppercase tracking-wider">Publishers</span>
            </div>
            <div class="text-center">
              <span class="block text-lg font-display text-victorian-gold-dark">
                {{ stats?.total_binders || 0 }}
              </span>
              <span class="text-xs text-victorian-ink-muted uppercase tracking-wider">Binders</span>
            </div>
            <div class="text-center">
              <span class="block text-lg font-display text-victorian-ink">
                {{ totalNodes }}
              </span>
              <span class="text-xs text-victorian-ink-muted uppercase tracking-wider">Total Nodes</span>
            </div>
          </div>

          <!-- Loading skeleton for stats -->
          <div v-else-if="loading" class="flex gap-4 mb-4 justify-center md:justify-start">
            <div v-for="i in 4" :key="i" class="text-center">
              <div class="h-6 w-8 bg-victorian-paper-antique rounded animate-pulse mx-auto mb-1"></div>
              <div class="h-3 w-12 bg-victorian-paper-antique rounded animate-pulse"></div>
            </div>
          </div>

          <!-- CTA -->
          <span
            class="inline-flex items-center gap-1 text-sm font-medium text-victorian-hunter-600 hover:text-victorian-hunter-800 transition-colors"
          >
            Explore social circles
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
