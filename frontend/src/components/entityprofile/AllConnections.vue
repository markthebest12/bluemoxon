<script setup lang="ts">
import type { ProfileConnection } from "@/types/entityProfile";

defineProps<{
  connections: ProfileConnection[];
}>();
</script>

<template>
  <section class="all-connections">
    <h2 class="all-connections__title">All Connections</h2>
    <div class="all-connections__list">
      <router-link
        v-for="conn in connections"
        :key="`${conn.entity.type}:${conn.entity.id}`"
        :to="{
          name: 'entity-profile',
          params: { type: conn.entity.type, id: conn.entity.id },
        }"
        class="all-connections__card"
      >
        <span class="all-connections__name">{{ conn.entity.name }}</span>
        <span class="all-connections__detail">
          {{ conn.connection_type.replace(/_/g, " ") }} &middot;
          {{ conn.shared_book_count }}
          {{ conn.shared_book_count === 1 ? "book" : "books" }}
        </span>
      </router-link>
    </div>
  </section>
</template>

<style scoped>
.all-connections__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.all-connections__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.all-connections__card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-surface, #faf8f5);
  border-radius: 6px;
  border: 1px solid var(--color-border, #e8e4de);
  text-decoration: none;
  color: inherit;
  transition: border-color 150ms;
}

.all-connections__card:hover {
  border-color: var(--color-accent-gold, #b8860b);
}

.all-connections__name {
  font-weight: 500;
}

.all-connections__detail {
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
}
</style>
