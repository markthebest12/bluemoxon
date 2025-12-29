<script setup lang="ts">
import { watch, onUnmounted } from "vue";

const props = defineProps<{
  visible: boolean;
}>();

defineEmits<{
  "backdrop-click": [];
}>();

// Track how many modals are open to handle nested modals correctly
let modalCount = 0;

watch(
  () => props.visible,
  (isVisible) => {
    if (isVisible) {
      modalCount++;
      document.body.style.overflow = "hidden";
    } else {
      modalCount--;
      if (modalCount <= 0) {
        modalCount = 0;
        document.body.style.overflow = "";
      }
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (props.visible) {
    modalCount--;
    if (modalCount <= 0) {
      modalCount = 0;
      document.body.style.overflow = "";
    }
  }
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-from-class="modal-backdrop-enter-from"
      enter-active-class="modal-backdrop-enter-active"
      leave-to-class="modal-backdrop-leave-to"
      leave-active-class="modal-backdrop-leave-active"
      appear
    >
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="$emit('backdrop-click')"
      >
        <Transition
          enter-from-class="modal-enter-from"
          enter-active-class="modal-enter-active"
          leave-to-class="modal-leave-to"
          leave-active-class="modal-leave-active"
          appear
        >
          <slot />
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
