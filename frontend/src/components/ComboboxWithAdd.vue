<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { UI_TIMING } from "@/constants";
import { getHttpStatus, isEntityConflictResponse, type EntitySuggestion } from "@/types/errors";

interface Option {
  id: number | null;
  name: string;
}

const props = defineProps<{
  label: string;
  options: Option[];
  modelValue: number | null;
  placeholder?: string;
  suggestedName?: string; // Pre-populate input when no match found
  createFn?: (name: string, force?: boolean) => Promise<{ id: number; name: string }>;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number | null];
  create: [name: string];
}>();

const searchText = ref("");
const isOpen = ref(false);
const conflictState = ref<{
  input: string;
  suggestions: EntitySuggestion[];
} | null>(null);
const isCreating = ref(false);

// Find selected option to display (supports null id for "All" options)
const selectedOption = computed(() => {
  if (!Array.isArray(props.options)) return null;
  return props.options.find((o) => o.id === props.modelValue) ?? null;
});

// Filter options based on search
const filteredOptions = computed(() => {
  if (!Array.isArray(props.options)) return [];
  if (!searchText.value) return props.options;
  const search = searchText.value.toLowerCase();
  return props.options.filter((o) => o.name.toLowerCase().includes(search));
});

// Show "add new" if search doesn't match any option exactly
const showAddNew = computed(() => {
  if (!searchText.value.trim()) return false;
  if (!Array.isArray(props.options)) return true;
  const search = searchText.value.toLowerCase().trim();
  return !props.options.some((o) => o.name.toLowerCase() === search);
});

// Update display when modelValue or suggestedName changes
watch(
  [() => props.modelValue, () => props.suggestedName],
  () => {
    if (selectedOption.value) {
      searchText.value = selectedOption.value.name;
    } else if (props.suggestedName && !searchText.value) {
      // Pre-populate with suggested name when no match found
      searchText.value = props.suggestedName;
    }
  },
  { immediate: true }
);

// Open dropdown when user types (if not already focused)
watch(searchText, (newVal, oldVal) => {
  // Only open on actual user input (not programmatic changes)
  if (newVal !== oldVal && newVal !== selectedOption.value?.name) {
    isOpen.value = true;
  }
});

function handleFocus(event: FocusEvent) {
  isOpen.value = true;
  conflictState.value = null; // Clear conflict when user starts new search
  // Select text instead of clearing so user can type to replace
  // but suggested name remains visible if they don't type
  const input = event.target as HTMLInputElement;
  input.select();
}

function handleBlur() {
  // Delay to allow click events to fire
  setTimeout(() => {
    isOpen.value = false;
    if (selectedOption.value) {
      searchText.value = selectedOption.value.name;
    } else if (props.suggestedName && !searchText.value.trim()) {
      // Restore suggested name if field is empty and no selection made
      searchText.value = props.suggestedName;
    }
  }, UI_TIMING.COMBOBOX_BLUR_DELAY_MS);
}

function selectOption(option: Option) {
  emit("update:modelValue", option.id);
  searchText.value = option.name;
  isOpen.value = false;
  conflictState.value = null; // Clear any conflict state when selecting
}

async function handleAddNew(force = false) {
  const name = searchText.value.trim();
  if (!name) return;

  // If createFn is provided, use it (with 409 handling)
  if (props.createFn) {
    isCreating.value = true;
    try {
      const result = await props.createFn(name, force);
      emit("update:modelValue", result.id);
      searchText.value = result.name;
      isOpen.value = false;
      conflictState.value = null;
    } catch (err: unknown) {
      if (getHttpStatus(err) === 409) {
        const response = (err as { response?: { data?: unknown } }).response?.data;
        if (isEntityConflictResponse(response)) {
          conflictState.value = {
            input: response.input,
            suggestions: response.suggestions,
          };
        }
        return;
      }
      // Re-throw non-409 errors for parent to handle
      throw err;
    } finally {
      isCreating.value = false;
    }
  } else {
    // Backward compatibility: emit create event
    emit("create", name);
  }
}

function selectSuggestion(suggestion: EntitySuggestion) {
  emit("update:modelValue", suggestion.id);
  searchText.value = suggestion.name;
  isOpen.value = false;
  conflictState.value = null;
}

async function handleForceCreate() {
  await handleAddNew(true);
}

function formatMatchPercent(match: number): string {
  return Math.round(match * 100) + "%";
}
</script>

<template>
  <div class="relative">
    <label class="block text-sm font-medium text-gray-700 mb-1">
      {{ label }}
    </label>
    <input
      v-model="searchText"
      type="text"
      :placeholder="placeholder || `Select or add ${label.toLowerCase()}`"
      class="input"
      @focus="handleFocus"
      @blur="handleBlur"
    />

    <!-- Dropdown -->
    <div
      v-if="isOpen && !conflictState"
      class="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto"
    >
      <!-- Filtered options -->
      <button
        v-for="(option, index) in filteredOptions"
        :key="option.id ?? `null-${index}`"
        type="button"
        data-testid="option"
        class="w-full px-3 py-2 text-left text-sm hover:bg-victorian-paper-aged"
        @mousedown.prevent="selectOption(option)"
      >
        {{ option.name }}
      </button>

      <!-- Add new option -->
      <button
        v-if="showAddNew"
        type="button"
        data-testid="add-new"
        class="w-full px-3 py-2 text-left text-sm text-victorian-hunter-700 hover:bg-victorian-paper-aged border-t border-victorian-paper-antique"
        :disabled="isCreating"
        @mousedown.prevent="handleAddNew(false)"
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

    <!-- Conflict suggestion panel -->
    <div
      v-if="conflictState"
      data-testid="suggestion-panel"
      class="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg"
    >
      <p class="text-sm text-amber-800 font-medium mb-2">
        Similar {{ label.toLowerCase() }} found:
      </p>
      <div
        v-for="suggestion in conflictState.suggestions"
        :key="suggestion.id"
        class="flex items-center justify-between py-1.5"
      >
        <div class="flex-1">
          <span class="text-sm font-medium text-gray-900">{{ suggestion.name }}</span>
          <span class="text-xs text-gray-500 ml-2">{{ formatMatchPercent(suggestion.match) }}</span>
          <span v-if="suggestion.book_count > 0" class="text-xs text-gray-500 ml-1">
            ({{ suggestion.book_count }} books)
          </span>
        </div>
        <button
          type="button"
          data-testid="use-suggestion"
          class="ml-2 px-2 py-1 text-xs font-medium text-white bg-victorian-hunter-600 hover:bg-victorian-hunter-700 rounded"
          @click="selectSuggestion(suggestion)"
        >
          Use
        </button>
      </div>
      <div class="mt-2 pt-2 border-t border-amber-200">
        <button
          type="button"
          data-testid="create-anyway"
          class="text-xs text-amber-700 hover:text-amber-900 underline"
          @click="handleForceCreate"
        >
          Create "{{ conflictState.input }}" anyway
        </button>
      </div>
    </div>
  </div>
</template>
