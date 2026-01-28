<script setup lang="ts">
interface Props {
  label: string;
  value: string | number;
  sublabel?: string;
  icon?: string;
}

defineProps<Props>();
</script>

<template>
  <div class="stat-card">
    <div v-if="icon" class="stat-icon">{{ icon }}</div>
    <div class="stat-value">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
    <div v-if="sublabel" class="stat-sublabel">{{ sublabel }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: var(--color-background-soft, #f8f6f1);
  border: 1px solid var(--color-border, #d4c9b8);
  border-radius: 4px;
  text-align: center;
}

.stat-icon {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  line-height: 1;
}

.stat-value {
  font-family: "Playfair Display", "Georgia", serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-heading, #2c1810);
  line-height: 1.1;
}

.stat-label {
  font-family: "Playfair Display", "Georgia", serif;
  font-size: 0.875rem;
  color: var(--color-text-muted, #6b5a4a);
  margin-top: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-sublabel {
  font-family: "Georgia", serif;
  font-size: 0.75rem;
  color: var(--color-text-muted, #8b7a6a);
  margin-top: 0.25rem;
  font-style: italic;
}
</style>
