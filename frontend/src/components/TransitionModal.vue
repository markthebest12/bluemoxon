<script setup lang="ts">
defineProps<{
  visible: boolean;
}>();

defineEmits<{
  'backdrop-click': [];
}>();
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-from-class="modal-backdrop-enter-from"
      enter-active-class="modal-backdrop-enter-active"
      leave-to-class="modal-backdrop-leave-to"
      leave-active-class="modal-backdrop-leave-active"
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
