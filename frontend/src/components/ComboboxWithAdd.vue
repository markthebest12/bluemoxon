<script setup lang="ts">
import { ref, computed, watch } from "vue";

interface Option {
  id: number;
  name: string;
}

const props = defineProps<{
  label: string;
  options: Option[];
  modelValue: number | null;
  placeholder?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number | null];
  create: [name: string];
}>();

const searchText = ref("");
const isOpen = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);

// Find selected option to display
const selectedOption = computed(() => {
  if (!props.modelValue) return null;
  return props.options.find((o) => o.id === props.modelValue);
});

// Filter options based on search
const filteredOptions = computed(() => {
  if (!searchText.value) return props.options;
  const search = searchText.value.toLowerCase();
  return props.options.filter((o) => o.name.toLowerCase().includes(search));
});

// Show "add new" if search doesn't match any option exactly
const showAddNew = computed(() => {
  if (!searchText.value.trim()) return false;
  const search = searchText.value.toLowerCase().trim();
  return !props.options.some((o) => o.name.toLowerCase() === search);
});

// Update display when modelValue changes
watch(
  () => props.modelValue,
  () => {
    if (selectedOption.value) {
      searchText.value = selectedOption.value.name;
    }
  },
  { immediate: true }
);

function handleFocus() {
  isOpen.value = true;
  searchText.value = "";
}

function handleInput() {
  // Open dropdown when user types
  isOpen.value = true;
}

function handleBlur() {
  // Delay to allow click events to fire
  setTimeout(() => {
    isOpen.value = false;
    if (selectedOption.value) {
      searchText.value = selectedOption.value.name;
    }
  }, 200);
}

function selectOption(option: Option) {
  emit("update:modelValue", option.id);
  searchText.value = option.name;
  isOpen.value = false;
}

function handleAddNew() {
  const name = searchText.value.trim();
  if (name) {
    emit("create", name);
  }
}
</script>

<template>
  <div class="relative">
    <label class="block text-sm font-medium text-gray-700 mb-1">
      {{ label }}
    </label>
    <input
      ref="inputRef"
      v-model="searchText"
      type="text"
      :placeholder="placeholder || `Select or add ${label.toLowerCase()}`"
      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      @focus="handleFocus"
      @input="handleInput"
      @blur="handleBlur"
    />

    <!-- Dropdown -->
    <div
      v-if="isOpen"
      class="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto"
    >
      <!-- Filtered options -->
      <button
        v-for="option in filteredOptions"
        :key="option.id"
        type="button"
        data-testid="option"
        class="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
        @mousedown.prevent="selectOption(option)"
      >
        {{ option.name }}
      </button>

      <!-- Add new option -->
      <button
        v-if="showAddNew"
        type="button"
        data-testid="add-new"
        class="w-full px-3 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 border-t border-gray-200"
        @mousedown.prevent="handleAddNew"
      >
        + Add "{{ searchText.trim() }}"
      </button>

      <!-- Empty state -->
      <div
        v-if="filteredOptions.length === 0 && !showAddNew"
        class="px-3 py-2 text-sm text-gray-500"
      >
        No options found
      </div>
    </div>
  </div>
</template>
