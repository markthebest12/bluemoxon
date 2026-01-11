<script setup lang="ts">
import { computed } from "vue";
import {
  BOOK_STATUSES,
  BOOK_STATUS_OPTIONS,
  CONDITION_GRADE_OPTIONS,
  PUBLISHER_TIER_OPTIONS,
} from "@/constants";
import type { Book } from "@/stores/books";
import { computeEra } from "@/utils/book-helpers";

// Props
const props = withDefaults(
  defineProps<{
    book: Book;
    isEditor: boolean;
    updatingStatus?: boolean;
  }>(),
  {
    updatingStatus: false,
  }
);

// Emits
const emit = defineEmits<{
  "status-changed": [newStatus: string];
}>();

// Computed properties
const conditionDisplay = computed(() => {
  const grade = props.book.condition_grade;
  if (!grade) return null;
  const option = CONDITION_GRADE_OPTIONS.find((c) => c.value === grade);
  // Fallback: show raw grade with empty description for unknown grades
  return option ?? { label: grade, description: "" };
});

// Helper functions
function getStatusColor(status: string): string {
  switch (status) {
    case BOOK_STATUSES.EVALUATING:
      return "bg-blue-100 text-blue-800";
    case BOOK_STATUSES.ON_HAND:
      return "bg-[var(--color-status-success-bg)] text-[var(--color-status-success-text)]";
    case BOOK_STATUSES.IN_TRANSIT:
      return "badge-transit";
    case BOOK_STATUSES.REMOVED:
      return "bg-[var(--color-status-error-bg)] text-[var(--color-status-error-text)]";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

function getStatusLabel(statusValue: string): string {
  const option = BOOK_STATUS_OPTIONS.find((s) => s.value === statusValue);
  // Fallback: replace all underscores with spaces for unknown statuses
  return option?.label ?? statusValue.replace(/_/g, " ");
}

function getTierLabel(tier: string | null): string {
  if (!tier) return "";
  const option = PUBLISHER_TIER_OPTIONS.find((t) => t.value === tier);
  // Fallback: replace all underscores with spaces for unknown tiers
  return option?.label ?? tier.replace(/_/g, " ");
}

// Event handlers
function onStatusChange(newStatus: string) {
  emit("status-changed", newStatus);
}
</script>

<template>
  <div class="space-y-6">
    <!-- Publication Details -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Publication Details</h2>
      <dl class="grid grid-cols-2 gap-4">
        <div>
          <dt class="text-sm text-gray-500">Publisher</dt>
          <dd class="font-medium">
            {{ book.publisher?.name || "-" }}
            <span v-if="book.publisher?.tier" class="text-xs text-moxon-600">
              ({{ getTierLabel(book.publisher.tier) }})
            </span>
            <!-- First Edition Badge -->
            <span
              v-if="book.is_first_edition"
              class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded-sm bg-amber-100 text-amber-800"
            >
              1st Edition
            </span>
            <!-- Provenance Badges -->
            <span
              v-if="book.has_provenance && book.provenance_tier === 'Tier 1'"
              class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded-sm bg-amber-100 text-amber-800"
            >
              Tier 1 Provenance
            </span>
            <span
              v-if="book.has_provenance && book.provenance_tier === 'Tier 2'"
              class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded-sm badge-transit"
            >
              Tier 2 Provenance
            </span>
            <span
              v-if="book.has_provenance && book.provenance_tier === 'Tier 3'"
              class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded-sm bg-gray-100 text-gray-800"
            >
              Tier 3 Provenance
            </span>
            <span
              v-if="book.has_provenance && !book.provenance_tier"
              class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded-sm bg-gray-100 text-gray-600"
            >
              Has Provenance
            </span>
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500">Date</dt>
          <dd class="font-medium">
            {{ book.publication_date || "-" }}
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500">Edition</dt>
          <dd class="font-medium">
            {{ book.edition || "-" }}
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500">Volumes</dt>
          <dd class="font-medium">
            {{ book.volumes }}
            <span
              v-if="!book.is_complete"
              class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded-sm bg-amber-100 text-amber-800"
            >
              Incomplete Set
            </span>
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500">Category</dt>
          <dd class="font-medium">
            {{ book.category || "-" }}
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500">Status</dt>
          <dd class="mt-1">
            <!-- Editors can change status -->
            <!-- min-w-[120px] fits longest status label "IN TRANSIT" with dropdown arrow -->
            <select
              v-if="isEditor"
              :value="book.status"
              :disabled="updatingStatus"
              :class="[
                'min-w-[120px] px-3 py-1.5 rounded-sm text-sm font-medium border-0 cursor-pointer no-print',
                getStatusColor(book.status),
                updatingStatus ? 'opacity-50' : '',
              ]"
              @change="onStatusChange(($event.target as HTMLSelectElement).value)"
            >
              <option
                v-for="status in BOOK_STATUS_OPTIONS"
                :key="status.value"
                :value="status.value"
              >
                {{ status.label }}
              </option>
            </select>
            <!-- Print-only status text for editors -->
            <span
              v-if="isEditor"
              :class="[
                'hidden print-only px-2 py-1 rounded-sm text-sm font-medium',
                getStatusColor(book.status),
              ]"
            >
              {{ getStatusLabel(book.status) }}
            </span>
            <!-- Viewers see read-only badge -->
            <span
              v-else
              :class="['px-2 py-1 rounded-sm text-sm font-medium', getStatusColor(book.status)]"
            >
              {{ getStatusLabel(book.status) }}
            </span>
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500">Condition</dt>
          <dd>
            <template v-if="conditionDisplay">
              <span class="font-medium">{{ conditionDisplay.label }}</span>
              <p v-if="conditionDisplay.description" class="text-xs text-gray-500 mt-0.5">
                {{ conditionDisplay.description }}
              </p>
            </template>
            <span v-else class="font-medium">-</span>
          </dd>
        </div>
        <div>
          <dt class="text-sm text-gray-500">Era</dt>
          <dd class="font-medium">
            {{ computeEra(book.year_start, book.year_end) || "-" }}
          </dd>
        </div>
      </dl>
      <!-- Condition Notes (full width, below grid) -->
      <div v-if="book.condition_notes" class="mt-4 pt-4 border-t border-gray-200">
        <dt class="text-sm text-gray-500 mb-1">Condition Notes</dt>
        <dd class="text-gray-700">{{ book.condition_notes }}</dd>
      </div>
    </div>

    <!-- Binding -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Binding</h2>
      <dl class="flex flex-col gap-2">
        <div>
          <dt class="text-sm text-gray-500">Type</dt>
          <dd class="font-medium">
            {{ book.binding_type || "-" }}
          </dd>
        </div>
        <div v-if="book.binding_authenticated">
          <dt class="text-sm text-gray-500">Bindery</dt>
          <dd class="font-medium text-victorian-burgundy">
            {{ book.binder?.name }} (Authenticated)
          </dd>
        </div>
        <div v-if="book.binding_description">
          <dt class="text-sm text-gray-500">Description</dt>
          <dd class="text-gray-700">
            {{ book.binding_description }}
          </dd>
        </div>
      </dl>
    </div>

    <!-- Notes -->
    <div v-if="book.notes" class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Notes</h2>
      <p class="text-gray-700 whitespace-pre-wrap">
        {{ book.notes }}
      </p>
    </div>
  </div>
</template>
