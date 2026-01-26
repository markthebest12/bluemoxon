<script setup lang="ts">
/**
 * NodeDetailPanel - Slide-out panel showing biographical information.
 */

interface Props {
  isOpen?: boolean;
  nodeId?: string;
  name?: string;
  nodeType?: "author" | "publisher" | "binder";
  birthYear?: number;
  deathYear?: number;
  era?: string;
  tier?: string;
  bookCount?: number;
  bookIds?: number[];
}

withDefaults(defineProps<Props>(), {
  isOpen: false,
  nodeId: undefined,
  name: undefined,
  nodeType: undefined,
  birthYear: undefined,
  deathYear: undefined,
  era: undefined,
  tier: undefined,
  bookCount: 0,
  bookIds: () => [],
});

const emit = defineEmits<{
  close: [];
  "view-book": [bookId: number];
}>();

function getTypeLabel(type?: string) {
  const labels: Record<string, string> = {
    author: "Author",
    publisher: "Publisher",
    binder: "Binder",
  };
  return labels[type || ""] || "Unknown";
}
</script>

<template>
  <Transition name="slide">
    <aside v-if="isOpen" class="node-detail-panel">
      <header class="node-detail-panel__header">
        <div>
          <span class="node-detail-panel__type">{{ getTypeLabel(nodeType) }}</span>
          <h2 class="node-detail-panel__name">{{ name || "Unknown" }}</h2>
        </div>
        <button class="node-detail-panel__close" @click="emit('close')">✕</button>
      </header>

      <div class="node-detail-panel__content">
        <!-- Dates -->
        <section v-if="birthYear || deathYear" class="node-detail-panel__section">
          <h3 class="node-detail-panel__section-title">Dates</h3>
          <p>{{ birthYear || "?" }} – {{ deathYear || "?" }}</p>
        </section>

        <!-- Era & Tier -->
        <section class="node-detail-panel__section">
          <div v-if="era" class="node-detail-panel__badge">{{ era }}</div>
          <div v-if="tier" class="node-detail-panel__badge node-detail-panel__badge--tier">
            {{ tier }}
          </div>
        </section>

        <!-- Books -->
        <section class="node-detail-panel__section">
          <h3 class="node-detail-panel__section-title">
            Books in Collection ({{ bookCount || 0 }})
          </h3>
          <p v-if="!bookIds?.length" class="text-sm text-victorian-ink-muted">No books linked</p>
          <ul v-else class="node-detail-panel__books">
            <li v-for="bookId in bookIds?.slice(0, 5)" :key="bookId">
              <button @click="emit('view-book', bookId)">Book #{{ bookId }}</button>
            </li>
          </ul>
        </section>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.node-detail-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 320px;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border-left: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.node-detail-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged);
}

.node-detail-panel__type {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--color-victorian-ink-muted);
}

.node-detail-panel__name {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-victorian-hunter-700);
  margin: 0.25rem 0 0;
}

.node-detail-panel__close {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--color-victorian-ink-muted);
  cursor: pointer;
  padding: 0.25rem;
}

.node-detail-panel__content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.node-detail-panel__section {
  margin-bottom: 1.5rem;
}

.node-detail-panel__section-title {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--color-victorian-ink-muted);
  margin-bottom: 0.5rem;
}

.node-detail-panel__badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: var(--color-victorian-hunter-100);
  color: var(--color-victorian-hunter-700);
  border-radius: 4px;
  margin-right: 0.5rem;
}

.node-detail-panel__badge--tier {
  background: var(--color-victorian-gold-light);
  color: var(--color-victorian-ink-dark);
}

.node-detail-panel__books {
  list-style: none;
  padding: 0;
  margin: 0;
}

.node-detail-panel__books button {
  background: none;
  border: none;
  color: var(--color-victorian-hunter-600);
  cursor: pointer;
  padding: 0.25rem 0;
  font-size: 0.875rem;
}

.node-detail-panel__books button:hover {
  text-decoration: underline;
}

/* Transition */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
