<script setup lang="ts">
/**
 * ActiveFilterPills - Shows active filters as removable pills.
 */

interface FilterPill {
  key: string;
  label: string;
  value: string;
}

interface Props {
  filters: FilterPill[];
}

defineProps<Props>();

const emit = defineEmits<{
  remove: [key: string];
  "clear-all": [];
}>();
</script>

<template>
  <div v-if="filters.length" class="active-filter-pills">
    <span class="active-filter-pills__label">Active:</span>
    <div class="active-filter-pills__list">
      <button
        v-for="filter in filters"
        :key="filter.key"
        class="active-filter-pills__pill"
        @click="emit('remove', filter.key)"
      >
        <span class="active-filter-pills__pill-label">{{ filter.label }}:</span>
        <span class="active-filter-pills__pill-value">{{ filter.value }}</span>
        <span class="active-filter-pills__pill-remove">×</span>
      </button>
    </div>
    <button v-if="filters.length > 1" class="active-filter-pills__clear" @click="emit('clear-all')">
      Clear all
    </button>
  </div>
</template>

<style scoped>
.active-filter-pills {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  flex-wrap: wrap;
}

.active-filter-pills__label {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted);
}

.active-filter-pills__list {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.active-filter-pills__pill {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-victorian-hunter-100);
  border: 1px solid var(--color-victorian-hunter-300);
  border-radius: 999px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.active-filter-pills__pill:hover {
  background: var(--color-victorian-hunter-200);
}

.active-filter-pills__pill-label {
  color: var(--color-victorian-ink-muted);
}

.active-filter-pills__pill-value {
  font-weight: 500;
  color: var(--color-victorian-hunter-700);
}

.active-filter-pills__pill-remove {
  margin-left: 0.25rem;
  color: var(--color-victorian-burgundy);
}

.active-filter-pills__clear {
  font-size: 0.75rem;
  color: var(--color-victorian-burgundy);
  background: none;
  border: none;
  cursor: pointer;
}

.active-filter-pills__clear:hover {
  text-decoration: underline;
}
</style>
