<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  bookId: number;
  provenance: string | null;
  isEditor: boolean;
}>();

const emit = defineEmits<{
  "provenance-saved": [newProvenance: string | null];
}>();

const provenanceEditing = ref(false);
const provenanceText = ref("");
const savingProvenance = ref(false);

function startEdit() {
  provenanceText.value = props.provenance || "";
  provenanceEditing.value = true;
}

function cancelEdit() {
  provenanceEditing.value = false;
  provenanceText.value = "";
}

function saveProvenance() {
  savingProvenance.value = true;
  const trimmedText = provenanceText.value.trim();
  const valueToEmit = trimmedText === "" ? null : trimmedText;
  emit("provenance-saved", valueToEmit);
  // Note: UI stays open - parent will call onSaveSuccess/onSaveError
}

// Exposed methods for parent to call after async save completes
function onSaveSuccess() {
  provenanceEditing.value = false;
  savingProvenance.value = false;
  provenanceText.value = "";
}

function onSaveError() {
  savingProvenance.value = false;
  // Keep edit mode open so user can retry
}

defineExpose({
  onSaveSuccess,
  onSaveError,
});
</script>

<template>
  <div class="card">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-800">Provenance</h2>
      <button
        v-if="isEditor && !provenanceEditing"
        class="text-sm text-moxon-600 hover:text-moxon-800"
        @click="startEdit"
      >
        {{ provenance ? "Edit" : "Add provenance" }}
      </button>
    </div>

    <!-- View mode -->
    <div v-if="!provenanceEditing">
      <p v-if="provenance" class="whitespace-pre-wrap text-gray-700">{{ provenance }}</p>
      <p v-else class="italic text-gray-400">No provenance information available.</p>
    </div>

    <!-- Edit mode -->
    <div v-else>
      <textarea
        v-model="provenanceText"
        class="w-full rounded-lg border border-gray-300 p-3 text-gray-700 focus:border-moxon-500 focus:ring-1 focus:ring-moxon-500"
        rows="4"
        placeholder="Enter provenance information..."
      ></textarea>
      <div class="mt-3 flex justify-end gap-2">
        <button
          class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
          @click="cancelEdit"
        >
          Cancel
        </button>
        <button
          class="rounded-lg bg-moxon-600 px-4 py-2 text-white hover:bg-moxon-700 disabled:opacity-50"
          :disabled="savingProvenance"
          @click="saveProvenance"
        >
          {{ savingProvenance ? "Saving..." : "Save" }}
        </button>
      </div>
    </div>
  </div>
</template>
