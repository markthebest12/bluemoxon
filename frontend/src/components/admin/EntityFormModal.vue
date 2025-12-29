<script setup lang="ts">
import { ref, computed, watch } from "vue";
import TransitionModal from "@/components/TransitionModal.vue";
import type { AuthorEntity, PublisherEntity, BinderEntity } from "@/types/admin";

type EntityType = "author" | "publisher" | "binder";
type Entity = AuthorEntity | PublisherEntity | BinderEntity;

const props = defineProps<{
  visible: boolean;
  entityType: EntityType;
  entity?: Entity | null;
  saving: boolean;
  error?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  save: [data: Partial<Entity>];
}>();

const tierOptions = [
  { value: "", label: "None" },
  { value: "TIER_1", label: "Tier 1" },
  { value: "TIER_2", label: "Tier 2" },
  { value: "TIER_3", label: "Tier 3" },
];

// Form state
const form = ref<Partial<Entity>>({});

const isEdit = computed(() => !!props.entity?.id);
const title = computed(() => {
  const label =
    props.entityType === "author"
      ? "Author"
      : props.entityType === "publisher"
        ? "Publisher"
        : "Binder";
  return isEdit.value ? `Edit ${label}` : `Add ${label}`;
});

// Reset form when entity changes
watch(
  () => props.entity,
  (newEntity) => {
    if (newEntity) {
      form.value = { ...newEntity };
    } else {
      form.value = {
        name: "",
        tier: null,
        preferred: false,
      };
    }
  },
  { immediate: true }
);

function handleSubmit() {
  if (!form.value.name?.trim()) return;
  emit("save", form.value);
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="emit('close')">
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-md mx-4 overflow-hidden"
    >
      <!-- Header -->
      <div
        class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center"
      >
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ title }}</h2>
        <button
          @click="emit('close')"
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="px-6 py-4 flex flex-col gap-4">
        <!-- Error -->
        <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded text-sm">
          {{ error }}
        </div>

        <!-- Name (all types) -->
        <label class="block">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Name *</span>
          <input
            v-model="form.name"
            type="text"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-victorian-hunter-500 focus:border-victorian-hunter-500"
          />
        </label>

        <!-- Tier (all types) -->
        <label class="block">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Tier</span>
          <select
            v-model="form.tier"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-victorian-hunter-500 focus:border-victorian-hunter-500"
          >
            <option v-for="opt in tierOptions" :key="opt.label" :value="opt.value || null">
              {{ opt.label }}
            </option>
          </select>
        </label>

        <!-- Preferred (all types) -->
        <label class="flex items-center gap-2">
          <input
            v-model="form.preferred"
            type="checkbox"
            class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-victorian-hunter-600 focus:ring-victorian-hunter-500"
          />
          <span class="text-sm text-gray-700 dark:text-gray-300">Preferred (+10 scoring bonus)</span>
        </label>

        <!-- Author-specific fields -->
        <template v-if="entityType === 'author'">
          <div class="grid grid-cols-2 gap-4">
            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Birth Year</span>
              <input
                v-model.number="(form as AuthorEntity).birth_year"
                type="number"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </label>
            <label class="block">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Death Year</span>
              <input
                v-model.number="(form as AuthorEntity).death_year"
                type="number"
                class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </label>
          </div>
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Era</span>
            <input
              v-model="(form as AuthorEntity).era"
              type="text"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
        </template>

        <!-- Publisher-specific fields -->
        <template v-if="entityType === 'publisher'">
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Founded Year</span>
            <input
              v-model.number="(form as PublisherEntity).founded_year"
              type="number"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Description</span>
            <textarea
              v-model="(form as PublisherEntity).description"
              rows="3"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
        </template>

        <!-- Binder-specific fields -->
        <template v-if="entityType === 'binder'">
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Full Name</span>
            <input
              v-model="(form as BinderEntity).full_name"
              type="text"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
          <label class="block">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              Authentication Markers
            </span>
            <textarea
              v-model="(form as BinderEntity).authentication_markers"
              rows="3"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </label>
        </template>
      </form>

      <!-- Footer -->
      <div
        class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3 bg-gray-50 dark:bg-gray-800/50"
      >
        <button
          type="button"
          @click="emit('close')"
          class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        >
          Cancel
        </button>
        <button
          @click="handleSubmit"
          :disabled="saving || !form.name?.trim()"
          class="px-4 py-2 text-sm bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ saving ? "Saving..." : isEdit ? "Save Changes" : "Create" }}
        </button>
      </div>
    </div>
  </TransitionModal>
</template>
