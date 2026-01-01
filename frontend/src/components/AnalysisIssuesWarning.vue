<script setup lang="ts">
import { formatAnalysisIssues } from "@/composables/useFormatters";
import BaseTooltip from "./BaseTooltip.vue";

defineProps<{
  issues: string[] | null | undefined;
}>();
</script>

<template>
  <BaseTooltip
    v-if="issues?.length"
    :content="formatAnalysisIssues(issues)"
    position="top"
  >
    <span
      class="text-amber-500 cursor-help"
      role="img"
      aria-label="Analysis has issues"
    >
      ⚠️
    </span>
  </BaseTooltip>
</template>
