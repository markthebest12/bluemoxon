<script setup lang="ts">
import type { RelationshipNarrative, NarrativeTrigger } from "@/types/entityProfile";
import { getToneStyle } from "@/composables/entityprofile/getToneStyle";

defineProps<{
  narrative: RelationshipNarrative;
  trigger: NarrativeTrigger;
}>();

const TRIGGER_LABELS: Record<NonNullable<NarrativeTrigger>, string> = {
  cross_era_bridge: "Cross-Era Bridge",
  social_circle: "Social Circle",
  hub_figure: "Hub Figure",
  influence_chain: "Influence Chain",
};
</script>

<template>
  <div class="gossip-panel" :class="`gossip-panel--${narrative.narrative_style}`">
    <span v-if="trigger" class="gossip-panel__trigger">
      {{ TRIGGER_LABELS[trigger] ?? trigger }}
    </span>

    <p class="gossip-panel__summary">{{ narrative.summary }}</p>

    <!-- Prose paragraph mode -->
    <div
      v-if="narrative.narrative_style === 'prose-paragraph' && narrative.details?.length"
      class="gossip-panel__prose"
    >
      <p
        v-for="(fact, i) in narrative.details"
        :key="i"
        class="gossip-panel__fact"
        :style="{ borderLeftColor: getToneStyle(fact.tone).color }"
      >
        <span v-if="fact.year" class="gossip-panel__year">{{ fact.year }}</span>
        {{ fact.text }}
      </p>
    </div>

    <!-- Bullet facts mode -->
    <ul
      v-else-if="narrative.narrative_style === 'bullet-facts' && narrative.details?.length"
      class="gossip-panel__bullets"
    >
      <li
        v-for="(fact, i) in narrative.details"
        :key="i"
        :style="{ borderLeftColor: getToneStyle(fact.tone).color }"
      >
        <span v-if="fact.year" class="gossip-panel__year">{{ fact.year }}</span>
        {{ fact.text }}
      </li>
    </ul>

    <!-- Timeline events mode -->
    <div v-else-if="narrative.details?.length" class="gossip-panel__timeline">
      <div
        v-for="(fact, i) in narrative.details"
        :key="i"
        class="gossip-panel__event"
        :style="{ borderLeftColor: getToneStyle(fact.tone).color }"
      >
        <span v-if="fact.year" class="gossip-panel__year gossip-panel__year--badge">
          {{ fact.year }}
        </span>
        <span class="gossip-panel__event-text">{{ fact.text }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gossip-panel {
  padding: 12px 0 0;
}

.gossip-panel__trigger {
  display: inline-block;
  padding: 2px 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-accent-gold, #b8860b);
  background: color-mix(in srgb, var(--color-accent-gold, #b8860b) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-accent-gold, #b8860b) 30%, transparent);
  border-radius: 12px;
  margin-bottom: 8px;
}

.gossip-panel__summary {
  font-size: 14px;
  line-height: 1.5;
  font-style: italic;
  color: var(--color-text, #2c2420);
  margin: 8px 0;
}

.gossip-panel__fact,
.gossip-panel__bullets li,
.gossip-panel__event {
  padding: 8px 12px;
  border-left: 3px solid var(--color-accent-gold, #b8860b);
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.gossip-panel__year {
  font-weight: 600;
  margin-right: 6px;
  color: var(--color-text-muted, #8b8579);
}

.gossip-panel__year--badge {
  display: inline-block;
  padding: 1px 6px;
  background: var(--color-surface, #faf8f5);
  border: 1px solid var(--color-border, #e8e4de);
  border-radius: 4px;
  font-size: 11px;
}

.gossip-panel__bullets {
  list-style: none;
  padding: 0;
  margin: 0;
}

.gossip-panel__timeline {
  position: relative;
}

.gossip-panel__event {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.gossip-panel__event-text {
  flex: 1;
}
</style>
