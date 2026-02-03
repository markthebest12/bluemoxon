<script setup lang="ts">
import { computed, ref } from "vue";
import type { ProfileBook } from "@/types/entityProfile";
import { bookDetailRoute } from "@/utils/routes";
import ConditionBadge from "./ConditionBadge.vue";

const props = defineProps<{
  books: ProfileBook[];
}>();

const showAll = ref(false);
const INITIAL_COUNT = 6;

const visibleBooks = computed(() => {
  if (showAll.value || props.books.length <= INITIAL_COUNT) {
    return props.books;
  }
  return props.books.slice(0, INITIAL_COUNT);
});
</script>

<template>
  <section class="entity-books">
    <h2 class="entity-books__title">Books in Collection ({{ books.length }})</h2>
    <div class="entity-books__list">
      <router-link
        v-for="book in visibleBooks"
        :key="book.id"
        :to="bookDetailRoute(book.id)"
        class="entity-books__card"
      >
        <img
          v-if="book.primary_image_url"
          :src="book.primary_image_url"
          :alt="book.title"
          loading="lazy"
          class="entity-books__thumbnail"
          data-testid="book-thumbnail"
        />
        <div class="entity-books__content">
          <span class="entity-books__book-title">{{ book.title }}</span>
          <div class="entity-books__book-meta">
            <span v-if="book.year">{{ book.year }}</span>
            <ConditionBadge v-if="book.condition" :condition="book.condition" />
            <span v-if="book.edition" class="entity-books__edition">{{ book.edition }}</span>
          </div>
        </div>
      </router-link>
    </div>
    <button
      v-if="books.length > INITIAL_COUNT && !showAll"
      class="entity-books__show-all"
      @click="showAll = true"
    >
      Show all {{ books.length }} books
    </button>
  </section>
</template>

<style scoped>
.entity-books__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.entity-books__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.entity-books__card {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--color-surface, #faf8f5);
  border-radius: 6px;
  border: 1px solid var(--color-border, #e8e4de);
  text-decoration: none;
  color: inherit;
  transition: border-color 150ms;
}

.entity-books__card:hover {
  border-color: var(--color-accent-gold, #b8860b);
}

.entity-books__thumbnail {
  width: 48px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}

.entity-books__content {
  flex: 1;
  min-width: 0;
}

.entity-books__book-title {
  font-weight: 500;
}

.entity-books__book-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
  margin-top: 4px;
}

.entity-books__show-all {
  margin-top: 12px;
  padding: 8px 16px;
  background: none;
  border: 1px solid var(--color-border, #e8e4de);
  border-radius: 6px;
  cursor: pointer;
  color: var(--color-accent-gold, #b8860b);
  width: 100%;
}

.entity-books__show-all:hover {
  background: var(--color-surface, #faf8f5);
}
</style>
