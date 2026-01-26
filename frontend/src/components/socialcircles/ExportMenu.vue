<script setup lang="ts">
/**
 * ExportMenu - Export and share functionality.
 */

import { ref } from 'vue';

const isOpen = ref(false);

const emit = defineEmits<{
  'export-png': [];
  'export-json': [];
  'share': [];
}>();

function toggleMenu() {
  isOpen.value = !isOpen.value;
}

function handleExport(type: 'png' | 'json') {
  if (type === 'png') {
    emit('export-png');
  } else {
    emit('export-json');
  }
  isOpen.value = false;
}

function handleShare() {
  emit('share');
  isOpen.value = false;
}
</script>

<template>
  <div class="export-menu">
    <button class="export-menu__trigger" @click="toggleMenu">
      Export ▾
    </button>

    <Transition name="fade">
      <div v-if="isOpen" class="export-menu__dropdown">
        <button class="export-menu__item" @click="handleExport('png')">
          <span class="export-menu__icon">🖼️</span>
          Export as PNG
        </button>
        <button class="export-menu__item" @click="handleExport('json')">
          <span class="export-menu__icon">📄</span>
          Export as JSON
        </button>
        <hr class="export-menu__divider" />
        <button class="export-menu__item" @click="handleShare">
          <span class="export-menu__icon">🔗</span>
          Copy Share Link
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.export-menu {
  position: relative;
}

.export-menu__trigger {
  padding: 0.5rem 1rem;
  background: var(--color-victorian-hunter-600);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.export-menu__trigger:hover {
  background: var(--color-victorian-hunter-700);
}

.export-menu__dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.5rem;
  background: var(--color-victorian-paper-white);
  border: 1px solid var(--color-victorian-paper-aged);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 180px;
  z-index: 100;
}

.export-menu__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  font-size: 0.875rem;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.export-menu__item:hover {
  background: var(--color-victorian-paper-cream);
}

.export-menu__icon {
  font-size: 1rem;
}

.export-menu__divider {
  margin: 0.25rem 0;
  border: none;
  border-top: 1px solid var(--color-victorian-paper-aged);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
