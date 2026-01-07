<script setup lang="ts">
interface BookProps {
  id: number;
  title: string;
}

interface Props {
  book: BookProps;
  isEditor: boolean;
}

defineProps<Props>();

defineEmits<{
  delete: [];
  print: [];
}>();
</script>

<template>
  <div class="flex gap-2">
    <!-- Print button (visible to all users) -->
    <button
      class="no-print text-victorian-ink-muted hover:text-victorian-ink-dark p-2 rounded-sm hover:bg-victorian-paper-cream transition-colors"
      title="Print this page"
      @click="$emit('print')"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
        />
      </svg>
    </button>
    <!-- Editor-only actions -->
    <template v-if="isEditor">
      <RouterLink
        :to="`/books/${book.id}/edit`"
        class="btn-secondary text-sm sm:text-base px-3 sm:px-4 no-print"
      >
        Edit Book
      </RouterLink>
      <button
        class="btn-danger text-sm sm:text-base px-3 sm:px-4 no-print"
        @click="$emit('delete')"
      >
        Delete
      </button>
    </template>
  </div>
</template>
