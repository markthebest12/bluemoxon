<script setup lang="ts">
import { formatAnalysisIssues } from "@/composables/useFormatters";

defineProps<{
  issues: string[] | null | undefined;
}>();
</script>

<template>
  <span
    v-if="issues?.length"
    class="text-amber-500"
    role="img"
    aria-label="Analysis has issues"
    :title="formatAnalysisIssues(issues)"
  >
    ⚠️
  </span>
</template>
