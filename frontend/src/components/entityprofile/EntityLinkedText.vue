<script setup lang="ts">
import { computed } from "vue";
import { parseEntityMarkers } from "@/utils/entityMarkers";
import type { ProfileConnection } from "@/types/entityProfile";

const props = defineProps<{
  text: string;
  connections: ProfileConnection[];
}>();

// Build a Set of valid entity keys for O(1) lookup
const validEntityKeys = computed(() => {
  const keys = new Set<string>();
  for (const conn of props.connections) {
    keys.add(`${conn.entity.type}:${conn.entity.id}`);
  }
  return keys;
});

const segments = computed(() => parseEntityMarkers(props.text));

function isValidLink(entityType: string, entityId: number): boolean {
  return validEntityKeys.value.has(`${entityType}:${entityId}`);
}
</script>

<template>
  <span class="entity-linked-text">
    <template v-for="(seg, i) in segments" :key="i">
      <router-link
        v-if="seg.type === 'link' && isValidLink(seg.entityType, seg.entityId)"
        :to="{
          name: 'entity-profile',
          params: { type: seg.entityType, id: String(seg.entityId) },
        }"
        class="entity-linked-text__link"
      >
        {{ seg.displayName }}
      </router-link>
      <template v-else-if="seg.type === 'link'">{{ seg.displayName }}</template>
      <template v-else>{{ seg.content }}</template>
    </template>
  </span>
</template>

<style scoped>
.entity-linked-text__link {
  color: inherit;
  text-decoration: underline dotted;
  text-underline-offset: 2px;
  cursor: pointer;
  transition:
    text-decoration-style 0.15s ease,
    color 0.15s ease;
}

.entity-linked-text__link:hover {
  text-decoration-style: solid;
  color: var(--color-accent-gold, #b8860b);
}
</style>
