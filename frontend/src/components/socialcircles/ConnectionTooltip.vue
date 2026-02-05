<!-- frontend/src/components/socialcircles/ConnectionTooltip.vue -->
<script setup lang="ts">
/**
 * ConnectionTooltip - Tooltip for edge hover showing relationship details.
 *
 * Features:
 * - Relationship type and strength display
 * - Evidence/description text
 * - Time period when applicable
 * - Shared books count
 * - Victorian styling with fade animation
 * - Smart positioning to avoid viewport clipping
 */

import { computed, ref, watch, nextTick } from "vue";
import type { ConnectionType } from "@/types/socialCircles";

// Connection type display info
const CONNECTION_LABELS: Record<ConnectionType, { label: string; description: string }> = {
  // Book-based connections
  publisher: {
    label: "Publisher Relationship",
    description: "Author was published by this publisher",
  },
  shared_publisher: {
    label: "Shared Publisher",
    description: "Both authors published by the same publisher",
  },
  binder: {
    label: "Same Bindery",
    description: "Books bound at the same bindery",
  },
  // AI-discovered connections
  family: {
    label: "Family",
    description: "Family relationship (marriage, siblings, etc.)",
  },
  friendship: {
    label: "Friendship",
    description: "Personal friends and social connections",
  },
  influence: {
    label: "Influence",
    description: "Mentorship or intellectual influence",
  },
  collaboration: {
    label: "Collaboration",
    description: "Literary partnership or co-authorship",
  },
  scandal: {
    label: "Scandal",
    description: "Affairs, feuds, or public controversies",
  },
};

interface Props {
  visible?: boolean;
  x?: number;
  y?: number;
  sourceName?: string;
  targetName?: string;
  connectionType: ConnectionType;
  strength?: number;
  evidence?: string;
  startYear?: number;
  endYear?: number;
  sharedBookCount?: number;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  x: 0,
  y: 0,
  sourceName: "",
  targetName: "",
  strength: undefined,
  evidence: undefined,
  startYear: undefined,
  endYear: undefined,
  sharedBookCount: undefined,
});

const tooltipRef = ref<HTMLDivElement | null>(null);
const adjustedPosition = ref({ x: 0, y: 0 });

// Adjust position to prevent viewport clipping
watch(
  () => [props.x, props.y, props.visible],
  async () => {
    if (!props.visible) return;
    await nextTick();

    if (tooltipRef.value) {
      const rect = tooltipRef.value.getBoundingClientRect();
      const viewportWidth = window.innerWidth;

      let x = props.x;
      let y = props.y;

      // Adjust horizontally - center on cursor, shift if clipping
      x = props.x - rect.width / 2;
      if (x + rect.width > viewportWidth - 16) {
        x = viewportWidth - rect.width - 16;
      }
      if (x < 16) x = 16;

      // Adjust vertically - prefer above cursor
      y = props.y - rect.height - 12;
      if (y < 16) {
        y = props.y + 20; // Below cursor if no room above
      }

      adjustedPosition.value = { x, y };
    }
  },
  { immediate: true }
);

const connectionInfo = computed(() => {
  return CONNECTION_LABELS[props.connectionType];
});

// Format strength as descriptive text
const strengthLabel = computed(() => {
  if (props.strength === undefined) return null;
  const s = props.strength;
  if (s >= 8) return "Very Strong";
  if (s >= 6) return "Strong";
  if (s >= 4) return "Moderate";
  if (s >= 2) return "Weak";
  return "Tenuous";
});

const strengthClass = computed(() => {
  if (props.strength === undefined) return "";
  const s = props.strength;
  if (s >= 8) return "very-strong";
  if (s >= 6) return "strong";
  if (s >= 4) return "moderate";
  return "weak";
});

// Format time period
const timePeriod = computed(() => {
  const { startYear, endYear } = props;
  if (!startYear && !endYear) return null;
  if (startYear && endYear) return `${startYear}–${endYear}`;
  if (startYear) return `From ${startYear}`;
  return `Until ${endYear}`;
});
</script>

<template>
  <Teleport to="body">
    <Transition name="tooltip-fade">
      <div
        v-if="visible"
        ref="tooltipRef"
        class="connection-tooltip"
        :style="{
          left: `${adjustedPosition.x}px`,
          top: `${adjustedPosition.y}px`,
        }"
      >
        <!-- Header with relationship type -->
        <div class="connection-tooltip__header">
          <span class="connection-tooltip__type">{{ connectionInfo?.label }}</span>
          <span v-if="strengthLabel" class="connection-tooltip__strength" :class="strengthClass">
            {{ strengthLabel }}
          </span>
        </div>

        <!-- Connection parties -->
        <div class="connection-tooltip__parties">
          <span class="connection-tooltip__name">{{ sourceName }}</span>
          <span class="connection-tooltip__connector">↔</span>
          <span class="connection-tooltip__name">{{ targetName }}</span>
        </div>

        <!-- Evidence/description -->
        <p v-if="evidence" class="connection-tooltip__evidence">"{{ evidence }}"</p>
        <p v-else-if="connectionInfo?.description" class="connection-tooltip__evidence">
          {{ connectionInfo.description }}
        </p>

        <!-- Footer with time period and shared books -->
        <div
          v-if="timePeriod || (sharedBookCount && sharedBookCount > 0)"
          class="connection-tooltip__footer"
        >
          <span v-if="timePeriod" class="connection-tooltip__time">
            {{ timePeriod }}
          </span>
          <span v-if="sharedBookCount && sharedBookCount > 0" class="connection-tooltip__books">
            {{ sharedBookCount }} {{ sharedBookCount === 1 ? "book" : "books" }} in collection
          </span>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.connection-tooltip {
  position: fixed;
  z-index: 1000;
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  min-width: 220px;
  max-width: 320px;
  box-shadow:
    0 4px 12px rgba(0, 0, 0, 0.1),
    0 1px 3px rgba(0, 0, 0, 0.06);
  pointer-events: none;
  font-family: Georgia, serif;
}

.connection-tooltip__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
}

.connection-tooltip__type {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-hunter-700, #254a3d);
}

.connection-tooltip__strength {
  font-size: 0.625rem;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  background-color: var(--color-victorian-paper-cream, #f5f2e9);
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.connection-tooltip__strength.very-strong {
  background-color: var(--color-victorian-hunter-100, #e8f0ed);
  color: var(--color-victorian-hunter-700, #254a3d);
}

.connection-tooltip__strength.strong {
  background-color: var(--color-victorian-gold-100, #fdf6e3);
  color: var(--color-victorian-gold-dark, #8b6914);
}

.connection-tooltip__strength.moderate {
  background-color: var(--color-victorian-paper-cream, #f5f2e9);
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.connection-tooltip__strength.weak {
  background-color: var(--color-victorian-paper-cream, #f5f2e9);
  color: var(--color-victorian-ink-light, #8a8a87);
}

.connection-tooltip__parties {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.connection-tooltip__name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-victorian-ink, #3a3a38);
}

.connection-tooltip__connector {
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-size: 0.75rem;
}

.connection-tooltip__evidence {
  font-size: 0.8125rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin: 0 0 0.5rem;
  line-height: 1.4;
  font-style: italic;
}

.connection-tooltip__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  margin-top: 0.25rem;
}

.connection-tooltip__time {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

.connection-tooltip__books {
  font-size: 0.75rem;
  color: var(--color-victorian-hunter-600, #2f5a4b);
}

/* Fade animation */
.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition:
    opacity 150ms ease,
    transform 150ms ease;
}

.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
