<script setup lang="ts">
import { computed } from "vue";

interface Props {
  status: "pending" | "success" | "failed" | null;
  archivedUrl?: string | null;
  showLabel?: boolean;
  showArchiveButton?: boolean;
  archiving?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showLabel: true,
  showArchiveButton: false,
  archiving: false,
});

const emit = defineEmits<{
  archive: [];
}>();

const canArchive = computed(() => {
  return props.showArchiveButton && (props.status === null || props.status === "failed");
});

const badgeClass = computed(() => {
  switch (props.status) {
    case "success":
      return "bg-green-100 text-green-800";
    case "pending":
      return "bg-yellow-100 text-yellow-800";
    case "failed":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-600";
  }
});

const badgeText = computed(() => {
  switch (props.status) {
    case "success":
      return "Archived";
    case "pending":
      return "Archiving...";
    case "failed":
      return "Archive Failed";
    default:
      return "Not Archived";
  }
});

const iconPath = computed(() => {
  switch (props.status) {
    case "success":
      return "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"; // check circle
    case "pending":
      return "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"; // clock
    case "failed":
      return "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"; // exclamation circle
    default:
      return "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"; // info circle
  }
});
</script>

<template>
  <div class="inline-flex items-center gap-1">
    <component
      :is="status === 'success' && archivedUrl ? 'a' : 'span'"
      :href="status === 'success' && archivedUrl ? archivedUrl : undefined"
      :target="status === 'success' && archivedUrl ? '_blank' : undefined"
      :rel="status === 'success' && archivedUrl ? 'noopener noreferrer' : undefined"
      :class="[
        badgeClass,
        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
        status === 'success' && archivedUrl ? 'hover:underline cursor-pointer' : '',
      ]"
      :title="status === 'success' && archivedUrl ? 'View archived page' : undefined"
    >
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="iconPath" />
      </svg>
      <span v-if="showLabel">{{ badgeText }}</span>
    </component>
    <button
      v-if="canArchive"
      @click="emit('archive')"
      :disabled="archiving"
      class="ml-1 text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
      :title="status === 'failed' ? 'Retry archive' : 'Archive now'"
    >
      <span v-if="archiving">⏳</span>
      <span v-else>📥 Archive</span>
    </button>
  </div>
</template>
