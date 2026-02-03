<script setup lang="ts">
import { computed } from "vue";
import { getConditionColor, formatConditionGrade } from "@/utils/conditionColors";

const props = defineProps<{
  condition: string;
}>();

const bgColor = computed(() => getConditionColor(props.condition));
const label = computed(() => formatConditionGrade(props.condition));

/** Grades with dark backgrounds need white text; lighter ones get dark text. */
const LIGHT_TEXT_GRADES = new Set(["FINE", "NEAR_FINE", "VERY_GOOD", "POOR", "UNGRADED"]);

const textColor = computed(() =>
  LIGHT_TEXT_GRADES.has(props.condition.toUpperCase()) ? "#ffffff" : "#1a1a1a"
);
</script>

<template>
  <span
    class="condition-badge"
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
