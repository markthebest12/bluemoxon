<script setup lang="ts">
import { computed, watch, nextTick, ref } from "vue";
import type { ProfileConnection } from "@/types/entityProfile";
import { bookDetailRoute, entityProfileRoute } from "@/utils/routes";
import ConditionBadge from "./ConditionBadge.vue";
import ConnectionGossipPanel from "./ConnectionGossipPanel.vue";
import EntityLinkedText from "./EntityLinkedText.vue";

const props = defineProps<{
  connection: ProfileConnection | null;
  /** All connections for EntityLinkedText cross-referencing */
  allConnections: ProfileConnection[];
  isOpen: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const sidebarRef = ref<HTMLElement | null>(null);

// Focus trap on open
watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      await nextTick();
      sidebarRef.value?.focus();
    }
  }
);

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    emit("close");
  }
}

const connectionLabel = computed(() => {
  if (!props.connection) return "";
  return props.connection.connection_type.replace(/_/g, " ");
});

const strengthDots = computed(() => {
  if (!props.connection) return 0;
  return Math.ceil(props.connection.strength / 2);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="sidebar-slide">
      <aside
        v-if="isOpen && connection"
        ref="sidebarRef"
        class="connection-sidebar"
        tabindex="-1"
        role="complementary"
        aria-label="Connection details"
        @keydown="handleKeydown"
      >
        <div class="connection-sidebar__header">
          <div class="connection-sidebar__header-content">
            <router-link
              :to="entityProfileRoute(connection.entity.type, connection.entity.id)"
              class="connection-sidebar__entity-name"
            >
              {{ connection.entity.name }}
            </router-link>
            <div class="connection-sidebar__type-row">
              <span class="connection-sidebar__type">{{ connectionLabel }}</span>
              <span v-if="connection.sub_type" class="connection-sidebar__sub-type">
                {{ connection.sub_type }}
              </span>
              <span v-if="connection.is_ai_discovered" class="connection-sidebar__ai-badge">
                AI
              </span>
            </div>
          </div>
          <button
            class="connection-sidebar__close"
            aria-label="Close sidebar"
            @click="emit('close')"
          >
            &times;
          </button>
        </div>

        <div class="connection-sidebar__body">
          <!-- Strength -->
          <div class="connection-sidebar__strength">
            <span class="connection-sidebar__strength-label">Strength</span>
            <span class="connection-sidebar__dots">
              <span v-for="i in 5" :key="i" :class="i <= strengthDots ? '--filled' : '--empty'"
                >&bull;</span
              >
            </span>
            <span v-if="connection.confidence !== undefined" class="connection-sidebar__confidence">
              {{ Math.round(connection.confidence * 100) }}% confidence
            </span>
          </div>

          <!-- Narrative -->
          <section v-if="connection.narrative" class="connection-sidebar__narrative">
            <p class="connection-sidebar__evidence">
              <EntityLinkedText :text="connection.narrative" :connections="allConnections" />
            </p>
          </section>

          <!-- Shared Books -->
          <section v-if="connection.shared_books?.length" class="connection-sidebar__books">
            <h4 class="connection-sidebar__section-title">
              {{ connection.shared_book_count }}
              {{ connection.shared_book_count === 1 ? "Shared Book" : "Shared Books" }}
            </h4>
            <ul class="connection-sidebar__book-list">
              <li
                v-for="book in connection.shared_books"
                :key="book.id"
                class="connection-sidebar__book-item"
              >
                <img
                  v-if="book.primary_image_url"
                  :src="book.primary_image_url"
                  :alt="book.title"
                  loading="lazy"
                  class="connection-sidebar__book-thumb"
                />
                <div class="connection-sidebar__book-info">
                  <router-link
                    :to="bookDetailRoute(book.id)"
                    class="connection-sidebar__book-title"
                  >
                    {{ book.title }}
                  </router-link>
                  <div class="connection-sidebar__book-meta">
                    <span v-if="book.year">{{ book.year }}</span>
                    <ConditionBadge v-if="book.condition" :condition="book.condition" />
                  </div>
                </div>
              </li>
            </ul>
          </section>

          <!-- Relationship Story -->
          <ConnectionGossipPanel
            v-if="connection.relationship_story"
            :narrative="connection.relationship_story"
            :trigger="connection.narrative_trigger"
            :connections="allConnections"
          />
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.connection-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 400px;
  max-width: 90vw;
  height: 100vh;
  background: var(--color-surface, #faf8f5);
  border-left: 1px solid var(--color-border, #e8e4de);
  box-shadow: -4px 0 16px rgb(0 0 0 / 8%);
  z-index: 50;
  display: flex;
  flex-direction: column;
  outline: none;
}

.connection-sidebar__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  border-bottom: 1px solid var(--color-border, #e8e4de);
  flex-shrink: 0;
}

.connection-sidebar__header-content {
  flex: 1;
  min-width: 0;
}

.connection-sidebar__entity-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
  display: block;
  margin-bottom: 4px;
}

.connection-sidebar__entity-name:hover {
  text-decoration: underline;
}

.connection-sidebar__type-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.connection-sidebar__type {
  font-size: 12px;
  text-transform: capitalize;
  color: var(--color-text-secondary, #6b6b6b);
}

.connection-sidebar__sub-type {
  font-size: 11px;
  background: var(--color-surface-secondary, #f0ece6);
  padding: 1px 6px;
  border-radius: 4px;
}

.connection-sidebar__ai-badge {
  font-size: 10px;
  font-weight: 700;
  color: #6366f1;
  background: #eef2ff;
  padding: 1px 5px;
  border-radius: 4px;
}

.connection-sidebar__close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--color-text-secondary, #6b6b6b);
  padding: 0 4px;
  line-height: 1;
}

.connection-sidebar__close:hover {
  color: var(--color-text-primary, #1a1a1a);
}

.connection-sidebar__body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.connection-sidebar__strength {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.connection-sidebar__strength-label {
  color: var(--color-text-secondary, #6b6b6b);
}

.connection-sidebar__dots .--filled {
  color: var(--color-accent-gold, #b8860b);
}

.connection-sidebar__dots .--empty {
  color: var(--color-border, #e8e4de);
}

.connection-sidebar__confidence {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-secondary, #6b6b6b);
}

.connection-sidebar__evidence {
  font-style: italic;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary, #1a1a1a);
}

.connection-sidebar__section-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 8px;
}

.connection-sidebar__book-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.connection-sidebar__book-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.connection-sidebar__book-thumb {
  width: 40px;
  height: 56px;
  object-fit: cover;
  border-radius: 2px;
  flex-shrink: 0;
}

.connection-sidebar__book-info {
  min-width: 0;
}

.connection-sidebar__book-title {
  font-size: 13px;
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
  display: block;
}

.connection-sidebar__book-title:hover {
  text-decoration: underline;
}

.connection-sidebar__book-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-secondary, #6b6b6b);
  margin-top: 2px;
}

/* Slide transition */
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: transform 0.25s ease;
}

.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  transform: translateX(100%);
}
</style>
