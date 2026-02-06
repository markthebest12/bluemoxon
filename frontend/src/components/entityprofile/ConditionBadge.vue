<script setup lang="ts">
import { computed } from "vue";
import { getConditionColor, formatConditionGrade, getLuminance } from "@/utils/conditionColors";

const props = defineProps<{
  condition: string;
}>();

const bgColor = computed(() => getConditionColor(props.condition));
const label = computed(() => formatConditionGrade(props.condition));

/** Use white text on dark backgrounds (luminance < 0.18 threshold per WCAG). */
const textColor = computed(() =>
  getLuminance(bgColor.value) < 0.18 ? "#ffffff" : "#1a1a1a"
);
</script>

<template>
  <span
    class="condition-badge"
    data-testid="condition-badge"
    :style="{
      backgroundColor: bgColor,
      color: textColor,
    }"
  >
    {{ label }}
  </span>
</template>

<style scoped>
.condition-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  font-size: 11px;
  line-height: 1;
  padding: 2px 8px;
  white-space: nowrap;
}
</style>
