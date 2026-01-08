<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";

export interface SelectOption {
  value: string;
  label: string;
  description: string;
}

const props = defineProps<{
  modelValue: string;
  options: readonly SelectOption[] | SelectOption[];
  placeholder?: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const isOpen = ref(false);
const highlightedIndex = ref(-1);
const containerRef = ref<HTMLElement | null>(null);
const buttonRef = ref<HTMLButtonElement | null>(null);
const listRef = ref<HTMLElement | null>(null);

// Find selected option to display
const selectedOption = computed(() => {
  if (!props.modelValue) return null;
  return props.options.find((o) => o.value === props.modelValue);
});

// Display text for the button
const displayText = computed(() => {
  if (selectedOption.value) {
    return selectedOption.value.label;
  }
  return props.placeholder || "Select an option";
});

function toggleDropdown() {
  if (props.disabled) return;
  if (isOpen.value) {
    closeDropdown();
  } else {
    openDropdown();
  }
}

function openDropdown() {
  if (props.disabled) return;
  isOpen.value = true;
  // Set highlighted index to selected option or first option
  const selectedIdx = props.options.findIndex((o) => o.value === props.modelValue);
  highlightedIndex.value = selectedIdx >= 0 ? selectedIdx : 0;
}

function closeDropdown() {
  isOpen.value = false;
  highlightedIndex.value = -1;
}

function selectOption(option: SelectOption) {
  emit("update:modelValue", option.value);
  closeDropdown();
  // Return focus to button
  buttonRef.value?.focus();
}

function handleKeydown(event: KeyboardEvent) {
  if (props.disabled) return;

  switch (event.key) {
    case "Enter":
    case " ":
      event.preventDefault();
      if (isOpen.value && highlightedIndex.value >= 0) {
        selectOption(props.options[highlightedIndex.value]);
      } else {
        toggleDropdown();
      }
      break;
    case "ArrowDown":
      event.preventDefault();
      if (!isOpen.value) {
        openDropdown();
      } else {
        highlightedIndex.value = Math.min(highlightedIndex.value + 1, props.options.length - 1);
        scrollToHighlighted();
      }
      break;
    case "ArrowUp":
      event.preventDefault();
      if (!isOpen.value) {
        openDropdown();
      } else {
        highlightedIndex.value = Math.max(highlightedIndex.value - 1, 0);
        scrollToHighlighted();
      }
      break;
    case "Escape":
      event.preventDefault();
      closeDropdown();
      break;
    case "Tab":
      // Let tab work naturally, but close dropdown
      closeDropdown();
      break;
    case "Home":
      if (isOpen.value) {
        event.preventDefault();
        highlightedIndex.value = 0;
        scrollToHighlighted();
      }
      break;
    case "End":
      if (isOpen.value) {
        event.preventDefault();
        highlightedIndex.value = props.options.length - 1;
        scrollToHighlighted();
      }
      break;
  }
}

function scrollToHighlighted() {
  if (listRef.value && highlightedIndex.value >= 0) {
    const items = listRef.value.querySelectorAll("[data-option]");
    const item = items[highlightedIndex.value] as HTMLElement;
    if (item) {
      item.scrollIntoView({ block: "nearest" });
    }
  }
}

function handleClickOutside(event: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    closeDropdown();
  }
}

function handleBlur(_event: FocusEvent) {
  // Check if focus is moving outside the component
  requestAnimationFrame(() => {
    if (containerRef.value && !containerRef.value.contains(document.activeElement)) {
      closeDropdown();
    }
  });
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<template>
  <div ref="containerRef" class="relative" @blur.capture="handleBlur">
    <!-- Trigger Button -->
    <button
      ref="buttonRef"
      type="button"
      class="input w-full text-left flex items-center justify-between"
      :class="{
        'opacity-50 cursor-not-allowed': disabled,
        'cursor-pointer': !disabled,
      }"
      :disabled="disabled"
      :aria-expanded="isOpen"
      aria-haspopup="listbox"
      @click="toggleDropdown"
      @keydown="handleKeydown"
    >
      <span :class="{ 'text-[var(--color-text-muted)]': !selectedOption }">
        {{ displayText }}
      </span>
      <svg
        class="w-4 h-4 text-gray-500 transition-transform"
        :class="{ 'rotate-180': isOpen }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Dropdown -->
    <Transition
      enter-active-class="transition ease-out duration-150"
      enter-from-class="opacity-0 translate-y-[-4px]"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-100"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-[-4px]"
    >
      <div
        v-if="isOpen"
        ref="listRef"
        role="listbox"
        class="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded-sm shadow-lg max-h-60 overflow-auto"
        :aria-activedescendant="highlightedIndex >= 0 ? `option-${highlightedIndex}` : undefined"
      >
        <div
          v-for="(option, index) in options"
          :id="`option-${index}`"
          :key="option.value"
          data-option
          role="option"
          :aria-selected="option.value === modelValue"
          class="px-3 py-2 cursor-pointer transition-colors"
          :class="{
            'bg-victorian-paper-aged': highlightedIndex === index,
            'bg-victorian-paper-cream': option.value === modelValue && highlightedIndex !== index,
          }"
          @click="selectOption(option)"
          @mouseenter="highlightedIndex = index"
        >
          <div class="text-sm font-medium text-gray-900">
            {{ option.label }}
          </div>
          <div class="text-xs text-gray-500 mt-0.5">
            {{ option.description }}
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
