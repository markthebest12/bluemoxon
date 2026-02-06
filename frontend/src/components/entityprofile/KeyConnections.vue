<script setup lang="ts">
import { ref, watch, toRef } from "vue";
import type { ProfileConnection } from "@/types/entityProfile";
import { useAnalytics } from "@/composables/socialcircles/useAnalytics";
import ConnectionGossipPanel from "./ConnectionGossipPanel.vue";
import ConditionBadge from "./ConditionBadge.vue";
import EntityLinkedText from "./EntityLinkedText.vue";
import { bookDetailRoute, entityProfileRoute } from "@/utils/routes";

const props = defineProps<{
  connections: ProfileConnection[];
}>();

const analytics = useAnalytics();
const expandedCards = ref<Record<string, boolean>>({});

// Reset expanded state when connections change (navigating between profiles)
watch(toRef(props, "connections"), () => {
  expandedCards.value = {};
});

function toggleCard(conn: ProfileConnection) {
  const key = `${conn.entity.type}:${conn.entity.id}`;
  const willExpand = !expandedCards.value[key];
  expandedCards.value[key] = willExpand;
  if (willExpand) {
    analytics.trackGossipExpanded(conn.entity.id, conn.entity.name);
  }
}

function handleConnectionClick(conn: ProfileConnection) {
  analytics.trackConnectionClicked(conn.connection_type, conn.entity.id, conn.entity.name);
}

function isExpanded(conn: ProfileConnection): boolean {
  return !!expandedCards.value[`${conn.entity.type}:${conn.entity.id}`];
}
</script>

<template>
  <section class="key-connections" data-testid="key-connections">
    <h2 class="key-connections__title">Key Connections</h2>
    <div class="key-connections__list">
      <div
        v-for="conn in connections"
        :key="`${conn.entity.type}:${conn.entity.id}`"
        class="key-connections__card"
      >
        <div class="key-connections__header">
          <router-link
            :to="entityProfileRoute(conn.entity.type, conn.entity.id)"
            class="key-connections__name"
            @click="handleConnectionClick(conn)"
          >
            {{ conn.entity.name }}
          </router-link>
          <div class="key-connections__type-group">
            <span class="key-connections__type">{{ conn.connection_type.replace(/_/g, " ") }}</span>
            <span v-if="conn.sub_type" class="key-connections__sub-type">{{ conn.sub_type }}</span>
            <span v-if="conn.is_ai_discovered" class="key-connections__ai-badge">AI</span>
          </div>
        </div>
        <p
          v-if="conn.narrative"
          class="key-connections__narrative"
          :class="{
            'key-connections__narrative--rumored':
              conn.confidence !== undefined && conn.confidence < 0.3,
          }"
        >
          <EntityLinkedText :text="conn.narrative" :connections="connections" />
        </p>
        <ul v-if="conn.shared_books.length" class="key-connections__books">
          <li v-for="book in conn.shared_books" :key="book.id" class="key-connections__book-item">
            <img
              v-if="book.primary_image_url"
              :src="book.primary_image_url"
              :alt="book.title"
              loading="lazy"
              class="key-connections__book-thumb"
              data-testid="book-thumbnail"
            />
            <router-link :to="bookDetailRoute(book.id)" class="key-connections__book-link">
              {{ book.title }}
            </router-link>
            <span v-if="book.year"> ({{ book.year }})</span>
            <ConditionBadge v-if="book.condition" :condition="book.condition" />
          </li>
        </ul>
        <div class="key-connections__meta">
          <span v-if="conn.shared_book_count > 0 || !conn.is_ai_discovered"
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
        <button
          v-if="conn.relationship_story"
          class="key-connections__story-toggle"
          :aria-expanded="isExpanded(conn)"
          @click="toggleCard(conn)"
        >
          {{ isExpanded(conn) ? "Hide story" : "View full story" }}
        </button>
        <ConnectionGossipPanel
          v-if="conn.relationship_story && isExpanded(conn)"
          :narrative="conn.relationship_story"
          :trigger="conn.narrative_trigger"
          :connections="connections"
        />
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

.key-connections__type-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.key-connections__sub-type {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 1px 6px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--color-accent-gold, #b8860b) 15%, transparent);
  color: var(--color-accent-gold, #b8860b);
}

.key-connections__ai-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--color-victorian-hunter-700, #254a3d);
  color: white;
  letter-spacing: 0.5px;
}

.key-connections__narrative {
  font-size: 14px;
  line-height: 1.5;
  font-style: italic;
  margin: 8px 0;
}

.key-connections__narrative--rumored {
  opacity: 0.8;
}

.key-connections__narrative--rumored::before {
  content: "Rumored: ";
  font-weight: 600;
  font-style: normal;
}

.key-connections__books {
  list-style: none;
  padding: 0;
  margin: 8px 0;
  font-size: 13px;
}

.key-connections__book-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.key-connections__book-thumb {
  width: 32px;
  height: 40px;
  object-fit: cover;
  border-radius: 3px;
  flex-shrink: 0;
}

.key-connections__books li {
  padding: 2px 0;
  color: var(--color-text-muted, #8b8579);
}

.key-connections__books li::before {
  content: "\2022";
  color: var(--color-accent-gold, #b8860b);
  margin-right: 6px;
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

.key-connections__story-toggle {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 12px;
  font-size: 12px;
  color: var(--color-accent-gold, #b8860b);
  background: none;
  border: 1px solid var(--color-accent-gold, #b8860b);
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 150ms;
}

.key-connections__story-toggle:hover {
  background: color-mix(in srgb, var(--color-accent-gold, #b8860b) 10%, transparent);
}

.key-connections__book-link {
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
}

.key-connections__book-link:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .key-connections__card {
    padding: 12px;
  }

  .key-connections__story-toggle {
    padding: 6px 14px;
    font-size: 13px;
  }
}
</style>
