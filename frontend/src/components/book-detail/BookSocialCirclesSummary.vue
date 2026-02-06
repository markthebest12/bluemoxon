<script setup lang="ts">
/**
 * Social Circles summary card for the book detail page (#1867).
 *
 * Shows a lightweight summary of connections for the book's entities
 * (author, publisher, binder) with a link to the full social circles view.
 */
import { onMounted, ref, computed } from "vue";
import { api } from "@/services/api";
import { handleApiError } from "@/utils/errorHandler";
import { BOOK_STATUSES } from "@/constants";

interface ConnectionHighlight {
  source_name: string;
  source_type: string;
  target_name: string;
  target_type: string;
  connection_type: string;
  strength: number;
  evidence: string | null;
}

interface SocialCirclesSummary {
  entity_count: number;
  connection_count: number;
  highlights: ConnectionHighlight[];
  entity_node_ids: string[];
}

interface Props {
  bookId: number;
  bookStatus: string;
}

const props = defineProps<Props>();

const loading = ref(false);
const summary = ref<SocialCirclesSummary | null>(null);

const isQualifying = computed(() => {
  return (
    props.bookStatus === BOOK_STATUSES.ON_HAND || props.bookStatus === BOOK_STATUSES.IN_TRANSIT
  );
});

const hasConnections = computed(() => {
  return summary.value && summary.value.connection_count > 0;
});

const socialCirclesLink = computed(() => {
  // Link to social circles view; if we have a primary entity, use it as search query
  if (summary.value?.entity_node_ids?.length) {
    return { path: "/social-circles" };
  }
  return { path: "/social-circles" };
});

function formatConnectionType(type: string): string {
  const labels: Record<string, string> = {
    publisher: "Published by",
    shared_publisher: "Shared publisher",
    binder: "Bound by",
    family: "Family",
    friendship: "Friends",
    influence: "Influence",
    collaboration: "Collaborators",
    scandal: "Scandal",
  };
  return labels[type] || type;
}

onMounted(async () => {
  if (!isQualifying.value) return;

  loading.value = true;
  try {
    const response = await api.get(`/books/${props.bookId}/social-circles-summary`);
    summary.value = response.data;
  } catch (e) {
    handleApiError(e, "Loading social circles summary");
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div v-if="isQualifying && (loading || hasConnections)" class="card">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">Social Circles</h2>
      <RouterLink
        v-if="hasConnections"
        :to="socialCirclesLink"
        class="text-sm text-moxon-600 hover:text-moxon-800 hover:underline"
      >
        View full network &rarr;
      </RouterLink>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex items-center gap-2 text-gray-500 text-sm">
      <svg
        class="animate-spin h-4 w-4"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      Loading connections...
    </div>

    <!-- Summary stats -->
    <div v-else-if="hasConnections && summary" class="space-y-4">
      <div class="flex gap-4 text-sm">
        <div class="flex items-center gap-1.5">
          <span class="font-semibold text-gray-700">{{ summary.entity_count }}</span>
          <span class="text-gray-500">{{
            summary.entity_count === 1 ? "entity" : "entities"
          }}</span>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="font-semibold text-gray-700">{{ summary.connection_count }}</span>
          <span class="text-gray-500">{{
            summary.connection_count === 1 ? "connection" : "connections"
          }}</span>
        </div>
      </div>

      <!-- Connection highlights -->
      <div v-if="summary.highlights.length > 0" class="space-y-2">
        <p class="text-xs font-medium text-gray-500 uppercase tracking-wide">Key Connections</p>
        <div
          v-for="(highlight, index) in summary.highlights"
          :key="index"
          class="flex items-start gap-2 text-sm"
        >
          <span
            class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
            :class="{
              'bg-blue-100 text-blue-700':
                highlight.connection_type === 'publisher' ||
                highlight.connection_type === 'shared_publisher',
              'bg-amber-100 text-amber-700': highlight.connection_type === 'binder',
              'bg-rose-100 text-rose-700':
                highlight.connection_type === 'family' || highlight.connection_type === 'scandal',
              'bg-emerald-100 text-emerald-700':
                highlight.connection_type === 'friendship' ||
                highlight.connection_type === 'collaboration',
              'bg-purple-100 text-purple-700': highlight.connection_type === 'influence',
            }"
          >
            {{ formatConnectionType(highlight.connection_type) }}
          </span>
          <span class="text-gray-700">
            <span class="font-medium">{{ highlight.source_name }}</span>
            <span class="text-gray-400 mx-1">&mdash;</span>
            <span class="font-medium">{{ highlight.target_name }}</span>
            <span v-if="highlight.evidence" class="text-gray-500 ml-1 text-xs italic">
              {{ highlight.evidence }}
            </span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
