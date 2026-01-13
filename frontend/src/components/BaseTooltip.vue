<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";

const props = defineProps<{
  content: string;
  position?: "top" | "bottom" | "left" | "right";
}>();

const isVisible = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const tooltipPosition = ref({ top: 0, left: 0 });

function updatePosition() {
  if (!triggerRef.value) return;

  const rect = triggerRef.value.getBoundingClientRect();
  const pos = props.position || "top";

  // Calculate position based on trigger element
  switch (pos) {
    case "top":
      tooltipPosition.value = {
        top: rect.top - 8, // Above with gap
        left: rect.left + rect.width / 2,
      };
      break;
    case "bottom":
      tooltipPosition.value = {
        top: rect.bottom + 8, // Below with gap
        left: rect.left + rect.width / 2,
      };
      break;
    case "left":
      tooltipPosition.value = {
        top: rect.top + rect.height / 2,
        left: rect.left - 8,
      };
      break;
    case "right":
      tooltipPosition.value = {
        top: rect.top + rect.height / 2,
        left: rect.right + 8,
      };
      break;
  }
}

function show() {
  updatePosition();
  isVisible.value = true;
}

function hide() {
  isVisible.value = false;
}

// Update position on scroll/resize while visible
function handleScrollResize() {
  if (isVisible.value) {
    updatePosition();
  }
}

onMounted(() => {
  window.addEventListener("scroll", handleScrollResize, true);
  window.addEventListener("resize", handleScrollResize);
});

onUnmounted(() => {
  window.removeEventListener("scroll", handleScrollResize, true);
  window.removeEventListener("resize", handleScrollResize);
});

const tooltipStyle = computed(() => {
  const pos = props.position || "top";
  const style: Record<string, string> = {
    position: "fixed",
    zIndex: "9999",
  };

  if (pos === "top" || pos === "bottom") {
    style.left = `${tooltipPosition.value.left}px`;
    style.transform = "translateX(-50%)";
    if (pos === "top") {
      style.bottom = `${window.innerHeight - tooltipPosition.value.top}px`;
    } else {
      style.top = `${tooltipPosition.value.top}px`;
    }
  } else {
    style.top = `${tooltipPosition.value.top}px`;
    style.transform = "translateY(-50%)";
    if (pos === "left") {
      style.right = `${window.innerWidth - tooltipPosition.value.left}px`;
    } else {
      style.left = `${tooltipPosition.value.left}px`;
    }
  }

  return style;
});

const arrowClass = computed(() => {
  const pos = props.position || "top";
  return {
    "top-full left-1/2 -translate-x-1/2 -mt-1": pos === "top",
    "bottom-full left-1/2 -translate-x-1/2 -mb-1": pos === "bottom",
    "left-full top-1/2 -translate-y-1/2 -ml-1": pos === "left",
    "right-full top-1/2 -translate-y-1/2 -mr-1": pos === "right",
  };
});
</script>

<template>
  <div
    ref="triggerRef"
    class="inline-block"
    tabindex="0"
    @mouseenter="show"
    @mouseleave="hide"
    @focus="show"
    @blur="hide"
    @keydown.escape="hide"
  >
    <slot />
    <Teleport to="body">
      <div
        v-show="isVisible"
        role="tooltip"
        class="px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg whitespace-pre-line max-w-xs"
        :style="tooltipStyle"
      >
        {{ content }}
        <div class="absolute w-2 h-2 bg-gray-900 transform rotate-45" :class="arrowClass" />
      </div>
    </Teleport>
  </div>
</template>
