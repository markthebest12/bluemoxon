<script setup lang="ts">
import { ref } from "vue";

defineProps<{
  content: string;
  position?: "top" | "bottom" | "left" | "right";
}>();

const isVisible = ref(false);
</script>

<template>
  <div
    class="relative inline-block"
    tabindex="0"
    @mouseenter="isVisible = true"
    @mouseleave="isVisible = false"
    @focus="isVisible = true"
    @blur="isVisible = false"
  >
    <slot />
    <div
      v-show="isVisible"
      role="tooltip"
      class="absolute z-50 px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg whitespace-pre-line max-w-xs"
      :class="{
        'bottom-full left-1/2 -translate-x-1/2 mb-1': position === 'top' || !position,
        'top-full left-1/2 -translate-x-1/2 mt-1': position === 'bottom',
        'right-full top-1/2 -translate-y-1/2 mr-1': position === 'left',
        'left-full top-1/2 -translate-y-1/2 ml-1': position === 'right',
      }"
    >
      {{ content }}
      <div
        class="absolute w-2 h-2 bg-gray-900 transform rotate-45"
        :class="{
          'top-full left-1/2 -translate-x-1/2 -mt-1': position === 'top' || !position,
          'bottom-full left-1/2 -translate-x-1/2 -mb-1': position === 'bottom',
          'left-full top-1/2 -translate-y-1/2 -ml-1': position === 'left',
          'right-full top-1/2 -translate-y-1/2 -mr-1': position === 'right',
        }"
      />
    </div>
  </div>
</template>
