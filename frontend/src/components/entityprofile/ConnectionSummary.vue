<script setup lang="ts">
import { computed } from "vue";
import type { ProfileConnection } from "@/types/entityProfile";

const MAX_NAMES = 3;

const props = defineProps<{
  connections: ProfileConnection[];
}>();

const keyNames = computed(() =>
  props.connections.filter((c) => c.is_key).map((c) => c.entity.name)
);

const displayNames = computed(() => keyNames.value.slice(0, MAX_NAMES));

// Total connections minus displayed key names = unnamed connections ("and N others")
const remaining = computed(() => props.connections.length - displayNames.value.length);
</script>

<template>
  <section v-if="connections.length > 0" class="connection-summary">
    <h2 class="connection-summary__title">Network</h2>
    <p class="connection-summary__text">
      Connected to {{ connections.length }}
      {{ connections.length === 1 ? "figure" : "figures" }}
      <template v-if="displayNames.length > 0">
        including {{ displayNames.join(", ") }}
        <template v-if="remaining > 0">
          and {{ remaining }} {{ remaining === 1 ? "other" : "others" }}
        </template>
      </template>
    </p>
  </section>
</template>

<style scoped>
.connection-summary__title {
  font-size: 20px;
  margin: 0 0 8px;
}

.connection-summary__text {
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-text-muted, #8b8579);
}
</style>
