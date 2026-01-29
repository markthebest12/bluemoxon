<script setup lang="ts">
import { computed } from "vue";

const MAX_BADGE_DISPLAY = 99;

interface Props {
  activeFilterCount?: number;
}

const props = defineProps<Props>();

defineEmits<{
  (e: "click"): void;
}>();

const badgeLabel = computed(() => {
  return props.activeFilterCount && props.activeFilterCount > MAX_BADGE_DISPLAY
    ? `${MAX_BADGE_DISPLAY}+`
    : `${props.activeFilterCount || ""}`;
});

const ariaLabel = computed(() => {
  if (!props.activeFilterCount) return "Filters";
  const count =
    props.activeFilterCount > MAX_BADGE_DISPLAY
      ? `${MAX_BADGE_DISPLAY}+`
      : props.activeFilterCount;
  return `Filters (${count} active)`;
});
</script>

<template>
  <button class="mobile-filter-fab" :aria-label="ariaLabel" @click="$emit('click')">
    <svg class="filter-icon" viewBox="0 0 24 24" width="24" height="24">
      <path d="M3 4h18v2H3V4zm3 7h12v2H6v-2zm3 7h6v2H9v-2z" fill="currentColor" />
    </svg>
    <span v-if="badgeLabel" class="badge" role="status">{{ badgeLabel }}</span>
  </button>
</template>

<style scoped>
.mobile-filter-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 100;

  display: flex;
  align-items: center;
  justify-content: center;

  min-width: 56px;
  min-height: 56px;
  padding: 16px;

  background-color: var(--color-surface, #f5f0e8);
  border: 1px solid var(--color-border, #d4c5b0);
  border-radius: 28px;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.12),
    0 1px 3px rgba(0, 0, 0, 0.08);

  color: var(--color-text-secondary, #6b5d4d);
  cursor: pointer;

  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.1s ease;
}

.mobile-filter-fab:hover {
  background-color: var(--color-surface-hover, #ebe5da);
  box-shadow:
    0 4px 12px rgba(0, 0, 0, 0.15),
    0 2px 4px rgba(0, 0, 0, 0.1);
}

.mobile-filter-fab:active {
  transform: scale(0.96);
}

.filter-icon {
  flex-shrink: 0;
}

.badge {
  position: absolute;
  top: -4px;
  right: -4px;

  display: flex;
  align-items: center;
  justify-content: center;

  min-width: 24px;
  height: 20px;
  padding: 0 6px;

  background-color: var(--color-primary, #8b7355);
  border-radius: 10px;

  color: var(--color-text-inverse, #fff);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}
</style>
