<script setup lang="ts">
import type { ProfileConnection } from "@/types/entityProfile";

defineProps<{
  connections: ProfileConnection[];
}>();
</script>

<template>
  <section class="key-connections">
    <h2 class="key-connections__title">Key Connections</h2>
    <div class="key-connections__list">
      <div
        v-for="conn in connections"
        :key="`${conn.entity.type}:${conn.entity.id}`"
        class="key-connections__card"
      >
        <div class="key-connections__header">
          <router-link
            :to="{
              name: 'entity-profile',
              params: { type: conn.entity.type, id: conn.entity.id },
            }"
            class="key-connections__name"
          >
            {{ conn.entity.name }}
          </router-link>
          <span class="key-connections__type">{{ conn.connection_type.replace("_", " ") }}</span>
        </div>
        <p v-if="conn.narrative" class="key-connections__narrative">
          {{ conn.narrative }}
        </p>
        <div class="key-connections__meta">
          <span
            >{{ conn.shared_book_count }}
            {{ conn.shared_book_count === 1 ? "shared book" : "shared books" }}</span
          >
          <span class="key-connections__strength">
            <span
              v-for="i in 5"
              :key="i"
              :class="i <= Math.ceil(conn.strength / 2) ? '--filled' : '--empty'"
            >
              &bull;
            </span>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.key-connections__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.key-connections__list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.key-connections__card {
  padding: 16px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  border: 1px solid var(--color-border, #e8e4de);
}

.key-connections__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.key-connections__name {
  font-weight: 600;
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
}

.key-connections__name:hover {
  text-decoration: underline;
}

.key-connections__type {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--color-text-muted, #8b8579);
}

.key-connections__narrative {
  font-size: 14px;
  line-height: 1.5;
  font-style: italic;
  margin: 8px 0;
}

.key-connections__meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
}

.key-connections__strength .--filled {
  color: var(--color-accent-gold, #b8860b);
}

.key-connections__strength .--empty {
  opacity: 0.3;
}
</style>
