<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import { useFocusTrap } from "@vueuse/integrations/useFocusTrap";
import { useScrollLock } from "@/composables/useScrollLock";

const props = defineProps<{
  visible: boolean;
}>();

defineEmits<{
  "backdrop-click": [];
}>();

const { lock, unlock } = useScrollLock();

// Focus trap setup
const modalContainerRef = ref<HTMLElement | null>(null);
const { activate, deactivate } = useFocusTrap(modalContainerRef, {
  immediate: false,
  allowOutsideClick: true,
  escapeDeactivates: false, // Let modal handle escape
  fallbackFocus: () => modalContainerRef.value || document.body,
});

watch(
  () => props.visible,
  async (isVisible) => {
    if (isVisible) {
      lock();
      // Wait for DOM to update before activating focus trap
      await nextTick();
      if (modalContainerRef.value) {
        try {
          activate();
        } catch (e) {
          // Log in non-test environments to aid debugging
          if (import.meta.env.MODE !== "test") {
            console.warn("Focus trap activation failed:", e);
          }
        }
      }
    } else {
      try {
        deactivate();
      } catch (e) {
        // Log in non-test environments to aid debugging
        if (import.meta.env.MODE !== "test") {
          console.warn("Focus trap deactivation failed:", e);
        }
      }
      unlock();
    }
  },
  { immediate: true }
);
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
        ref="modalContainerRef"
        data-testid="modal-container"
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
