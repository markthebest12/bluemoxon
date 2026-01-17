<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { refDebounced } from "@/composables/useDebounce";
import { api } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import { getErrorMessage } from "@/types/errors";
import type {
  SystemInfoResponse,
  CostResponse,
  EntityTier,
  AuthorEntity,
  PublisherEntity,
  BinderEntity,
} from "@/types/admin";
import EntityManagementTable from "@/components/admin/EntityManagementTable.vue";
import EntityFormModal from "@/components/admin/EntityFormModal.vue";
import ReassignDeleteModal from "@/components/admin/ReassignDeleteModal.vue";
import OrphanCleanupPanel from "@/components/admin/OrphanCleanupPanel.vue";

// Tab state
const activeTab = ref<"settings" | "status" | "scoring" | "reference" | "costs" | "maintenance">(
  "settings"
);

// Cleanup panel state
const cleanupExpanded = ref(false);
const cleanupLoading = ref<string | null>(null);
const cleanupResult = ref<{
  stale_archived?: number;
  sources_checked?: number;
  sources_expired?: number;
  orphans_found?: number;
  orphans_deleted?: number;
  archives_retried?: number;
  archives_succeeded?: number;
  archives_failed?: number;
} | null>(null);
const cleanupError = ref<string | null>(null);

async function runCleanup(action: string, deleteOrphans = false) {
  if (cleanupLoading.value) return;
  cleanupLoading.value = action;
  cleanupResult.value = null;
  cleanupError.value = null;

  try {
    const response = await api.post("/admin/cleanup", {
      action,
      delete_orphans: deleteOrphans,
    });
    cleanupResult.value = response.data;
  } catch (e: unknown) {
    cleanupError.value = getErrorMessage(e, "Cleanup failed");
  } finally {
    cleanupLoading.value = null;
  }
}

// Settings tab (existing functionality)
const config = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 });
const saving = ref(false);
const settingsMessage = ref("");

// System info (for other tabs)
const systemInfo = ref<SystemInfoResponse | null>(null);
const loadingInfo = ref(false);
const infoError = ref("");

// Cost data
const costData = ref<CostResponse | null>(null);
const loadingCost = ref(false);
const costError = ref("");

// Entity management state
const authors = ref<AuthorEntity[]>([]);
const publishers = ref<PublisherEntity[]>([]);
const binders = ref<BinderEntity[]>([]);
const loadingEntities = ref({ authors: false, publishers: false, binders: false });
const entityError = ref<string | null>(null);

// Track entities currently being saved (for per-row loading indicator)
const savingEntityIds = ref<Set<string>>(new Set());

// Search filters - individual refs for debouncing
const authorSearch = ref("");
const publisherSearch = ref("");
const binderSearch = ref("");

// Debounced search filters (300ms delay for performance)
const debouncedAuthorSearch = refDebounced(authorSearch, 300);
const debouncedPublisherSearch = refDebounced(publisherSearch, 300);
const debouncedBinderSearch = refDebounced(binderSearch, 300);

// Collapsed sections
const collapsedSections = ref({ authors: false, publishers: false, binders: false });

// Modal state
type EntityType = "author" | "publisher" | "binder";
const formModal = ref({
  visible: false,
  entityType: "author" as EntityType,
  entity: null as EntityTier | null,
  saving: false,
  error: null as string | null,
});

const deleteModal = ref({
  visible: false,
  entityType: "author" as EntityType,
  entity: null as EntityTier | null,
  processing: false,
  error: null as string | null,
});

// Permission check
const authStore = useAuthStore();
const canEdit = computed(() => authStore.isEditor);

// Key tunables to highlight in scoring config
const keyTunables = new Set([
  "publisher_tier_1",
  "publisher_tier_2",
  "binder_tier_1",
  "binder_tier_2",
  "author_priority_cap",
  "publisher_match",
  "new_author",
  "quality",
  "strategic_fit",
  "strategic_floor",
  "quality_floor",
]);

const isKeyTunable = (key: string) => keyTunables.has(key);

onMounted(async () => {
  await loadConfig();
  await loadSystemInfo();
});

async function loadConfig() {
  try {
    const res = await api.get("/admin/config");
    config.value = res.data;
  } catch (e) {
    console.error("Failed to load config:", e);
  }
}

async function saveConfig() {
  saving.value = true;
  settingsMessage.value = "";
  try {
    await api.put("/admin/config", config.value);
    settingsMessage.value = "Saved successfully";
    setTimeout(() => {
      settingsMessage.value = "";
    }, 3000);
  } catch (e) {
    settingsMessage.value = "Failed to save";
    console.error("Failed to save config:", e);
  } finally {
    saving.value = false;
  }
}

async function loadSystemInfo() {
  loadingInfo.value = true;
  infoError.value = "";
  try {
    const res = await api.get("/admin/system-info");
    systemInfo.value = res.data;
  } catch (e) {
    infoError.value = "Failed to load system info";
    console.error("Failed to load system info:", e);
  } finally {
    loadingInfo.value = false;
  }
}

async function refreshSystemInfo() {
  await loadSystemInfo();
}

async function fetchCostData(forceRefresh = false) {
  loadingCost.value = true;
  costError.value = "";
  try {
    // Pass browser timezone so MTD calculation uses local time
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const params: Record<string, string | boolean> = { timezone };
    if (forceRefresh) {
      params.refresh = true;
    }
    const res = await api.get("/admin/costs", { params });
    costData.value = res.data;
  } catch (e) {
    costError.value = "Failed to load cost data";
    console.error("Failed to load cost data:", e);
  } finally {
    loadingCost.value = false;
  }
}

// Entity management functions
async function loadEntities() {
  loadingEntities.value = { authors: true, publishers: true, binders: true };
  try {
    const [authorsRes, publishersRes, bindersRes] = await Promise.all([
      api.get("/authors"),
      api.get("/publishers"),
      api.get("/binders"),
    ]);
    authors.value = authorsRes.data;
    publishers.value = publishersRes.data;
    binders.value = bindersRes.data;
  } catch (e) {
    console.error("Failed to load entities:", e);
  } finally {
    loadingEntities.value = { authors: false, publishers: false, binders: false };
  }
}

function getEntitiesByType(type: EntityType): EntityTier[] {
  switch (type) {
    case "author":
      return authors.value;
    case "publisher":
      return publishers.value;
    case "binder":
      return binders.value;
  }
}

function getEntityLabel(type: EntityType): string {
  switch (type) {
    case "author":
      return "Author";
    case "publisher":
      return "Publisher";
    case "binder":
      return "Binder";
  }
}

function toggleSection(type: EntityType) {
  const key = (type + "s") as "authors" | "publishers" | "binders";
  collapsedSections.value[key] = !collapsedSections.value[key];
}

// Show error and auto-clear after 5 seconds
function showEntityError(message: string) {
  entityError.value = message;
  setTimeout(() => {
    entityError.value = null;
  }, 5000);
}

// Helper to create entity saving key
function getSavingKey(type: EntityType, id: number): string {
  return `${type}-${id}`;
}

// Inline update handlers with lock to prevent race conditions
async function handleTierUpdate(type: EntityType, id: number, tier: string | null) {
  const key = getSavingKey(type, id);

  // Lock: if already saving this entity, ignore the request
  if (savingEntityIds.value.has(key)) {
    return;
  }

  entityError.value = null;
  savingEntityIds.value = new Set([...savingEntityIds.value, key]);

  const endpoint = `/${type}s/${id}`;
  try {
    await api.put(endpoint, { tier });
    // Update local state
    const entities = getEntitiesByType(type);
    const entity = entities.find((e) => e.id === id);
    if (entity) entity.tier = tier;
  } catch (e) {
    console.error(`Failed to update ${type} tier:`, e);
    showEntityError(`Failed to update tier. Please try again.`);
    // Reload to revert
    await loadEntities();
  } finally {
    const newSet = new Set(savingEntityIds.value);
    newSet.delete(key);
    savingEntityIds.value = newSet;
  }
}

async function handlePreferredUpdate(type: EntityType, id: number, preferred: boolean) {
  const key = getSavingKey(type, id);

  // Lock: if already saving this entity, ignore the request
  if (savingEntityIds.value.has(key)) {
    return;
  }

  entityError.value = null;
  savingEntityIds.value = new Set([...savingEntityIds.value, key]);

  const endpoint = `/${type}s/${id}`;
  try {
    await api.put(endpoint, { preferred });
    // Update local state
    const entities = getEntitiesByType(type);
    const entity = entities.find((e) => e.id === id);
    if (entity) entity.preferred = preferred;
  } catch (e) {
    console.error(`Failed to update ${type} preferred:`, e);
    showEntityError(`Failed to update preferred status. Please try again.`);
    await loadEntities();
  } finally {
    const newSet = new Set(savingEntityIds.value);
    newSet.delete(key);
    savingEntityIds.value = newSet;
  }
}

// Modal handlers
function openCreateModal(type: EntityType) {
  formModal.value = {
    visible: true,
    entityType: type,
    entity: null,
    saving: false,
    error: null,
  };
}

function openEditModal(type: EntityType, entity: EntityTier) {
  formModal.value = {
    visible: true,
    entityType: type,
    entity,
    saving: false,
    error: null,
  };
}

function closeFormModal() {
  formModal.value.visible = false;
}

async function handleFormSave(type: EntityType, data: Partial<EntityTier>) {
  formModal.value.saving = true;
  formModal.value.error = null;

  try {
    if (formModal.value.entity?.id) {
      // Update
      await api.put(`/${type}s/${formModal.value.entity.id}`, data);
    } else {
      // Create
      await api.post(`/${type}s`, data);
    }
    closeFormModal();
    await loadEntities();
  } catch (e: unknown) {
    formModal.value.error = getErrorMessage(e, "Failed to save");
  } finally {
    formModal.value.saving = false;
  }
}

function openDeleteModal(type: EntityType, entity: EntityTier) {
  deleteModal.value = {
    visible: true,
    entityType: type,
    entity,
    processing: false,
    error: null,
  };
}

function closeDeleteModal() {
  deleteModal.value.visible = false;
}

async function handleDeleteDirect(type: EntityType) {
  if (!deleteModal.value.entity) return;
  deleteModal.value.processing = true;
  deleteModal.value.error = null;

  try {
    await api.delete(`/${type}s/${deleteModal.value.entity.id}`);
    closeDeleteModal();
    await loadEntities();
  } catch (e: unknown) {
    deleteModal.value.error = getErrorMessage(e, "Failed to delete");
  } finally {
    deleteModal.value.processing = false;
  }
}

async function handleReassignDelete(type: EntityType, targetId: number) {
  if (!deleteModal.value.entity) return;
  deleteModal.value.processing = true;
  deleteModal.value.error = null;

  try {
    await api.post(`/${type}s/${deleteModal.value.entity.id}/reassign`, {
      target_id: targetId,
    });
    closeDeleteModal();
    await loadEntities();
  } catch (e: unknown) {
    deleteModal.value.error = getErrorMessage(e, "Failed to reassign and delete");
    // Refresh entities so dropdown shows current state (target may have been deleted)
    await loadEntities();
  } finally {
    deleteModal.value.processing = false;
  }
}

// Computed helpers
const hasHealthIssues = computed(() => {
  if (!systemInfo.value) return false;
  return systemInfo.value.health.overall !== "healthy";
});

const healthStatusClass = (status: string) => {
  switch (status) {
    case "healthy":
      return "text-[var(--color-status-success-accent)]";
    case "unhealthy":
      return "text-[var(--color-status-error-accent)]";
    case "skipped":
      return "text-gray-400";
    default:
      return "text-[var(--color-status-warning-accent)]";
  }
};

const healthIcon = (status: string) => {
  switch (status) {
    case "healthy":
      return "✓";
    case "unhealthy":
      return "✗";
    case "skipped":
      return "○";
    default:
      return "!";
  }
};

function formatDeployTime(isoString: string | undefined): string {
  if (!isoString || isoString === "unknown") return "N/A";
  try {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return isoString;
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatCurrency(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

function formatCostDate(dateStr: string): string {
  // Parse as UTC date to avoid timezone shift (AWS returns dates like "2025-12-27")
  const [year, month, day] = dateStr.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

const maxDailyCost = computed(() => {
  if (!costData.value?.daily_trend.length) return 0;
  return Math.max(...costData.value.daily_trend.map((d) => d.cost));
});

function getBarWidth(cost: number): string {
  if (!maxDailyCost.value) return "0%";
  return `${(cost / maxDailyCost.value) * 100}%`;
}
</script>

<template>
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-2xl font-bold mb-6">Admin Configuration</h1>

    <!-- Health Alert Banner -->
    <div
      v-if="hasHealthIssues && systemInfo"
      class="mb-4 p-4 bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] rounded-lg"
    >
      <div class="flex items-center gap-2 text-[var(--color-status-error-text)]">
        <span class="text-xl">⚠️</span>
        <span class="font-medium">System health issues detected</span>
        <span class="text-sm text-[var(--color-status-error-accent)]">
          ({{ systemInfo.health.overall }})
        </span>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="border-b border-gray-200 mb-6 overflow-x-auto">
      <nav class="-mb-px flex gap-4 sm:gap-8 min-w-max">
        <button
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'settings'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="activeTab = 'settings'"
        >
          Settings
        </button>
        <button
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'status'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="activeTab = 'status'"
        >
          System Status
        </button>
        <button
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'scoring'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="activeTab = 'scoring'"
        >
          Scoring Config
        </button>
        <button
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'reference'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="
            activeTab = 'reference';
            if (!authors.length) loadEntities();
          "
        >
          Reference Data
        </button>
        <button
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'costs'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="
            activeTab = 'costs';
            if (!costData) fetchCostData();
          "
        >
          Costs
        </button>
        <button
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'maintenance'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="activeTab = 'maintenance'"
        >
          Maintenance
        </button>
      </nav>
    </div>

    <!-- Settings Tab -->
    <div
      v-if="activeTab === 'settings'"
      class="bg-white rounded-lg shadow-sm p-6 flex flex-col gap-4"
    >
      <h2 class="text-lg font-semibold">Currency Conversion Rates</h2>
      <div class="grid grid-cols-2 gap-4">
        <label class="block">
          <span class="text-sm text-gray-700">GBP to USD</span>
          <input
            v-model.number="config.gbp_to_usd_rate"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-sm border-gray-300 shadow-xs"
          />
        </label>
        <label class="block">
          <span class="text-sm text-gray-700">EUR to USD</span>
          <input
            v-model.number="config.eur_to_usd_rate"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded-sm border-gray-300 shadow-xs"
          />
        </label>
      </div>
      <div class="flex items-center gap-4">
        <button :disabled="saving" class="btn-primary" @click="saveConfig">
          {{ saving ? "Saving..." : "Save" }}
        </button>
        <span v-if="settingsMessage" class="text-sm text-[var(--color-status-success-accent)]">{{
          settingsMessage
        }}</span>
      </div>
    </div>

    <!-- System Status Tab -->
    <div v-else-if="activeTab === 'status'" class="flex flex-col gap-6">
      <div class="flex justify-end">
        <button
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-sm"
          @click="refreshSystemInfo"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div
        v-if="infoError"
        class="p-4 bg-[var(--color-status-error-bg)] text-[var(--color-status-error-text)] rounded-sm"
      >
        {{ infoError }}
      </div>

      <div v-else-if="systemInfo" class="flex flex-col gap-6">
        <!-- Version & Deployment -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Version & Deployment</h3>
          <dl class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt class="text-gray-500">App Version</dt>
              <dd class="font-mono">{{ systemInfo.system.version }}</dd>
            </div>
            <div class="overflow-hidden">
              <dt class="text-gray-500">Git SHA</dt>
              <dd class="font-mono truncate" :title="systemInfo.system.git_sha">
                {{ systemInfo.system.git_sha?.slice(0, 7) || "N/A" }}
              </dd>
            </div>
            <div>
              <dt class="text-gray-500">Deploy Time</dt>
              <dd class="font-mono">{{ formatDeployTime(systemInfo.system.deploy_time) }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Environment</dt>
              <dd class="font-mono">{{ systemInfo.system.environment }}</dd>
            </div>
          </dl>
          <div v-if="systemInfo.is_cold_start" class="mt-4 text-sm text-amber-600">
            ⚡ Cold Start - latencies may be elevated
          </div>
        </div>

        <!-- Health Checks -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Health Checks</h3>
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="healthStatusClass(systemInfo.health.checks.database.status)">
                  {{ healthIcon(systemInfo.health.checks.database.status) }}
                </span>
                <span>Database</span>
                <span class="text-xs text-gray-400">
                  ({{ systemInfo.health.checks.database.book_count }} books)
                </span>
              </div>
              <span class="text-sm text-gray-500">
                {{ systemInfo.health.checks.database.latency_ms }}ms
              </span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="healthStatusClass(systemInfo.health.checks.s3.status)">
                  {{ healthIcon(systemInfo.health.checks.s3.status) }}
                </span>
                <span>S3 Images</span>
                <span class="text-xs text-gray-400">
                  ({{ systemInfo.health.checks.s3.bucket }})
                </span>
              </div>
              <span class="text-sm text-gray-500">
                {{ systemInfo.health.checks.s3.latency_ms }}ms
              </span>
            </div>
            <div v-if="systemInfo.health.checks.sqs" class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="healthStatusClass(systemInfo.health.checks.sqs.status)">
                  {{ healthIcon(systemInfo.health.checks.sqs.status) }}
                </span>
                <span>SQS Queues</span>
                <span v-if="systemInfo.health.checks.sqs.reason" class="text-xs text-gray-400">
                  ({{ systemInfo.health.checks.sqs.reason }})
                </span>
              </div>
              <span class="text-sm text-gray-500">
                {{ systemInfo.health.checks.sqs.latency_ms || "-" }}ms
              </span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="healthStatusClass(systemInfo.health.checks.cognito.status)">
                  {{ healthIcon(systemInfo.health.checks.cognito.status) }}
                </span>
                <span>Cognito</span>
                <span v-if="systemInfo.health.checks.cognito.reason" class="text-xs text-gray-400">
                  ({{ systemInfo.health.checks.cognito.reason }})
                </span>
              </div>
              <span class="text-sm text-gray-500">
                {{ systemInfo.health.checks.cognito.latency_ms || "-" }}ms
              </span>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t text-sm text-gray-500">
            Total latency: {{ systemInfo.health.total_latency_ms }}ms
          </div>
        </div>

        <!-- Bedrock Models -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Bedrock Models</h3>
          <dl class="flex flex-col gap-3 text-sm">
            <div
              v-for="(model, key) in systemInfo.models"
              :key="key"
              class="border-b border-gray-100 pb-2 last:border-0"
            >
              <dt class="font-medium text-gray-900">{{ key }}</dt>
              <dd class="text-gray-500 text-xs">{{ model.usage }}</dd>
              <dd class="font-mono text-xs text-gray-400 mt-0.5">
                {{ model.model_id }}
              </dd>
            </div>
          </dl>
        </div>

        <!-- Infrastructure -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Infrastructure</h3>
          <dl class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt class="text-gray-500">AWS Region</dt>
              <dd class="font-mono">{{ systemInfo.infrastructure.aws_region }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Images Bucket</dt>
              <dd class="font-mono">{{ systemInfo.infrastructure.images_bucket }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Backup Bucket</dt>
              <dd class="font-mono">{{ systemInfo.infrastructure.backup_bucket }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">CDN URL</dt>
              <dd class="font-mono text-xs truncate">
                {{ systemInfo.infrastructure.images_cdn_url || "Not configured" }}
              </dd>
            </div>
            <div>
              <dt class="text-gray-500">Analysis Queue</dt>
              <dd class="font-mono text-xs">
                {{ systemInfo.infrastructure.analysis_queue || "Not configured" }}
              </dd>
            </div>
            <div>
              <dt class="text-gray-500">Eval Runbook Queue</dt>
              <dd class="font-mono text-xs">
                {{ systemInfo.infrastructure.eval_runbook_queue || "Not configured" }}
              </dd>
            </div>
            <div>
              <dt class="text-gray-500">Image Processing Queue</dt>
              <dd class="font-mono text-xs">
                {{ systemInfo.infrastructure.image_processing_queue || "Not configured" }}
              </dd>
            </div>
          </dl>
        </div>

        <!-- Limits & Timeouts -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Limits & Timeouts</h3>
          <dl class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt class="text-gray-500">Bedrock Read Timeout</dt>
              <dd class="font-mono">{{ systemInfo.limits.bedrock_read_timeout_sec }}s</dd>
            </div>
            <div>
              <dt class="text-gray-500">Bedrock Connect Timeout</dt>
              <dd class="font-mono">{{ systemInfo.limits.bedrock_connect_timeout_sec }}s</dd>
            </div>
            <div>
              <dt class="text-gray-500">Max Image Size</dt>
              <dd class="font-mono">{{ formatBytes(systemInfo.limits.image_max_bytes) }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Safe Image Size</dt>
              <dd class="font-mono">{{ formatBytes(systemInfo.limits.image_safe_bytes) }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Prompt Cache TTL</dt>
              <dd class="font-mono">{{ systemInfo.limits.prompt_cache_ttl_sec }}s</dd>
            </div>
            <div>
              <dt class="text-gray-500">Presigned URL Expiry</dt>
              <dd class="font-mono">{{ systemInfo.limits.presigned_url_expiry_sec }}s (1 hour)</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>

    <!-- Scoring Config Tab -->
    <div v-else-if="activeTab === 'scoring'" class="flex flex-col gap-6">
      <div class="flex justify-between items-center">
        <p class="text-sm text-gray-500">★ = Key tunable</p>
        <button
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-sm"
          @click="refreshSystemInfo"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="systemInfo" class="grid md:grid-cols-2 gap-6">
        <!-- Quality Points -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Quality Score Points</h3>
          <dl class="flex flex-col gap-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.quality_points"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded-sm': isKeyTunable(String(key)) }"
            >
              <dt>
                <span v-if="isKeyTunable(String(key))" class="text-yellow-600">★ </span>
                {{ String(key).replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">{{ value }} pts</dd>
            </div>
          </dl>
        </div>

        <!-- Strategic Points -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Strategic Fit Points</h3>
          <dl class="flex flex-col gap-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.strategic_points"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded-sm': isKeyTunable(String(key)) }"
            >
              <dt>
                <span v-if="isKeyTunable(String(key))" class="text-yellow-600">★ </span>
                {{ String(key).replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">{{ value }} pts</dd>
            </div>
          </dl>
        </div>

        <!-- Thresholds -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Thresholds</h3>
          <dl class="flex flex-col gap-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.thresholds"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded-sm': isKeyTunable(String(key)) }"
            >
              <dt>
                <span v-if="isKeyTunable(String(key))" class="text-yellow-600">★ </span>
                {{ String(key).replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">
                {{ String(key).includes("price") ? `${(Number(value) * 100).toFixed(0)}%` : value }}
              </dd>
            </div>
          </dl>
        </div>

        <!-- Weights -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Combined Score Weights</h3>
          <dl class="flex flex-col gap-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.weights"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded-sm': isKeyTunable(String(key)) }"
            >
              <dt>
                <span v-if="isKeyTunable(String(key))" class="text-yellow-600">★ </span>
                {{ String(key).replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">{{ (Number(value) * 100).toFixed(0) }}%</dd>
            </div>
          </dl>
        </div>

        <!-- Offer Discounts -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Offer Discounts</h3>
          <dl class="flex flex-col gap-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.offer_discounts"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded-sm': isKeyTunable(String(key)) }"
            >
              <dt>
                <span v-if="isKeyTunable(String(key))" class="text-yellow-600">★ </span>
                {{
                  String(key).includes("-")
                    ? `Score ${String(key)}`
                    : String(key).replace(/_/g, " ")
                }}
              </dt>
              <dd class="font-mono">{{ (Number(value) * 100).toFixed(0) }}% below FMV</dd>
            </div>
          </dl>
        </div>

        <!-- Era Boundaries -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Era Boundaries</h3>
          <dl class="flex flex-col gap-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.era_boundaries"
              :key="key"
              class="flex justify-between"
            >
              <dt>{{ String(key).replace(/_/g, " ") }}</dt>
              <dd class="font-mono">{{ value }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>

    <!-- Reference Data Tab -->
    <div v-else-if="activeTab === 'reference'" class="flex flex-col gap-6">
      <!-- Error message -->
      <div
        v-if="entityError"
        class="p-4 bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] rounded-lg text-[var(--color-status-error-text)] text-sm"
      >
        {{ entityError }}
      </div>

      <!-- Authors Section -->
      <div class="bg-white rounded-lg shadow-sm">
        <button
          class="w-full px-6 py-4 flex items-center justify-between text-left border-b border-gray-200"
          @click="toggleSection('author')"
        >
          <h3 class="text-lg font-semibold text-gray-900">Authors</h3>
          <svg
            class="w-5 h-5 text-gray-500 transition-transform"
            :class="{ 'rotate-180': !collapsedSections.authors }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
        <div v-if="!collapsedSections.authors" class="p-6">
          <input
            v-model="authorSearch"
            type="text"
            placeholder="Search authors..."
            class="mb-4 w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900"
          />
          <EntityManagementTable
            entity-type="author"
            :entities="authors"
            :loading="loadingEntities.authors"
            :can-edit="canEdit"
            :search-query="debouncedAuthorSearch"
            :saving-ids="savingEntityIds"
            @update:tier="(id, tier) => handleTierUpdate('author', id, tier)"
            @update:preferred="(id, pref) => handlePreferredUpdate('author', id, pref)"
            @edit="(e) => openEditModal('author', e)"
            @delete="(e) => openDeleteModal('author', e)"
            @create="openCreateModal('author')"
          />
        </div>
      </div>

      <!-- Publishers Section -->
      <div class="bg-white rounded-lg shadow-sm">
        <button
          class="w-full px-6 py-4 flex items-center justify-between text-left border-b border-gray-200"
          @click="toggleSection('publisher')"
        >
          <h3 class="text-lg font-semibold text-gray-900">Publishers</h3>
          <svg
            class="w-5 h-5 text-gray-500 transition-transform"
            :class="{ 'rotate-180': !collapsedSections.publishers }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
        <div v-if="!collapsedSections.publishers" class="p-6">
          <input
            v-model="publisherSearch"
            type="text"
            placeholder="Search publishers..."
            class="mb-4 w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900"
          />
          <EntityManagementTable
            entity-type="publisher"
            :entities="publishers"
            :loading="loadingEntities.publishers"
            :can-edit="canEdit"
            :search-query="debouncedPublisherSearch"
            :saving-ids="savingEntityIds"
            @update:tier="(id, tier) => handleTierUpdate('publisher', id, tier)"
            @update:preferred="(id, pref) => handlePreferredUpdate('publisher', id, pref)"
            @edit="(e) => openEditModal('publisher', e)"
            @delete="(e) => openDeleteModal('publisher', e)"
            @create="openCreateModal('publisher')"
          />
        </div>
      </div>

      <!-- Binders Section -->
      <div class="bg-white rounded-lg shadow-sm">
        <button
          class="w-full px-6 py-4 flex items-center justify-between text-left border-b border-gray-200"
          @click="toggleSection('binder')"
        >
          <h3 class="text-lg font-semibold text-gray-900">Binders</h3>
          <svg
            class="w-5 h-5 text-gray-500 transition-transform"
            :class="{ 'rotate-180': !collapsedSections.binders }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
        <div v-if="!collapsedSections.binders" class="p-6">
          <input
            v-model="binderSearch"
            type="text"
            placeholder="Search binders..."
            class="mb-4 w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900"
          />
          <EntityManagementTable
            entity-type="binder"
            :entities="binders"
            :loading="loadingEntities.binders"
            :can-edit="canEdit"
            :search-query="debouncedBinderSearch"
            :saving-ids="savingEntityIds"
            @update:tier="(id, tier) => handleTierUpdate('binder', id, tier)"
            @update:preferred="(id, pref) => handlePreferredUpdate('binder', id, pref)"
            @edit="(e) => openEditModal('binder', e)"
            @delete="(e) => openDeleteModal('binder', e)"
            @create="openCreateModal('binder')"
          />
        </div>
      </div>
    </div>

    <!-- Costs Tab -->
    <div v-else-if="activeTab === 'costs'" class="flex flex-col gap-6">
      <div class="flex justify-end gap-2">
        <button
          :disabled="loadingCost"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-sm"
          title="Uses server cache (up to 1 hour old)"
          @click="fetchCostData(false)"
        >
          {{ loadingCost ? "Loading..." : "Refresh" }}
        </button>
        <button
          :disabled="loadingCost"
          class="px-3 py-1 text-sm bg-victorian-hunter-100 hover:bg-victorian-hunter-200 text-victorian-hunter-700 rounded-sm"
          title="Bypass server cache and fetch fresh data from AWS"
          @click="fetchCostData(true)"
        >
          {{ loadingCost ? "Loading..." : "Force Refresh" }}
        </button>
      </div>

      <div
        v-if="costError"
        class="p-4 bg-[var(--color-status-error-bg)] text-[var(--color-status-error-text)] rounded-sm"
      >
        {{ costError }}
      </div>

      <div v-else-if="loadingCost && !costData" class="text-center py-8 text-gray-500">
        Loading cost data...
      </div>

      <div v-else-if="costData" class="flex flex-col gap-6">
        <!-- Bedrock Model Costs -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Bedrock Model Costs (MTD)</h3>
          <div v-if="costData.error" class="p-3 bg-yellow-50 text-yellow-700 rounded-sm mb-4">
            {{ costData.error }}
          </div>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-gray-500 border-b">
                <th class="pb-2">Model</th>
                <th class="pb-2">Usage</th>
                <th class="pb-2 text-right">Cost</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="model in costData.bedrock_models"
                :key="model.model_name"
                class="border-b border-gray-100"
              >
                <td class="py-2 font-medium">{{ model.model_name }}</td>
                <td class="py-2 text-gray-500">{{ model.usage }}</td>
                <td class="py-2 text-right font-mono">{{ formatCurrency(model.mtd_cost) }}</td>
              </tr>
              <tr class="font-semibold bg-gray-50">
                <td class="py-2" colspan="2">Total Bedrock</td>
                <td class="py-2 text-right font-mono">
                  {{ formatCurrency(costData.bedrock_total) }}
                </td>
              </tr>
            </tbody>
          </table>
          <p class="mt-4 text-xs text-gray-400">
            Period: {{ costData.period_start }} to {{ costData.period_end }}
          </p>
        </div>

        <!-- Daily Trend -->
        <div v-if="costData.daily_trend.length > 0" class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Daily Bedrock Trend (Last 14 Days)</h3>
          <div class="flex flex-col gap-2">
            <div
              v-for="day in costData.daily_trend"
              :key="day.date"
              class="flex items-center gap-3"
            >
              <span class="text-xs text-gray-500 w-16">{{ formatCostDate(day.date) }}</span>
              <div class="flex-1 h-5 bg-gray-100 rounded-sm overflow-hidden">
                <div class="h-full progress-bar" :style="{ width: getBarWidth(day.cost) }"></div>
              </div>
              <span class="text-xs font-mono w-16 text-right">{{ formatCurrency(day.cost) }}</span>
            </div>
          </div>
          <p class="mt-3 text-xs text-gray-400">
            Only shows days with Bedrock API usage. Days with $0 Bedrock spend are not displayed.
            AWS Cost Explorer data has a 24-48 hour delay.
          </p>
        </div>

        <!-- Other AWS Costs -->
        <div
          v-if="Object.keys(costData.other_costs).length > 0"
          class="bg-white rounded-lg shadow-sm p-6"
        >
          <details>
            <summary class="text-lg font-semibold cursor-pointer">Other AWS Costs</summary>
            <dl class="mt-4 flex flex-col gap-2 text-sm">
              <div
                v-for="(cost, service) in costData.other_costs"
                :key="service"
                class="flex justify-between"
              >
                <dt>{{ service }}</dt>
                <dd class="font-mono">{{ formatCurrency(cost) }}</dd>
              </div>
            </dl>
          </details>
        </div>

        <!-- Total -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <div class="flex justify-between items-center">
            <span class="text-lg font-semibold">Total AWS Cost (MTD)</span>
            <span class="text-2xl font-bold font-mono">{{
              formatCurrency(costData.total_aws_cost)
            }}</span>
          </div>
          <p class="mt-2 text-xs text-gray-400">
            Cached at: {{ formatDeployTime(costData.cached_at) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Maintenance Tab -->
    <div v-else-if="activeTab === 'maintenance'" class="flex flex-col gap-6">
      <div class="bg-white rounded-lg shadow-sm overflow-hidden">
        <button
          class="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50"
          @click="cleanupExpanded = !cleanupExpanded"
        >
          <span class="font-semibold text-gray-900 flex items-center gap-2">
            <span class="text-lg" aria-hidden="true">🧹</span>
            Cleanup Tools
          </span>
          <svg
            class="w-5 h-5 text-gray-500 transition-transform"
            :class="{ 'rotate-180': cleanupExpanded }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        <div v-if="cleanupExpanded" class="px-6 pb-6 border-t border-gray-100">
          <p class="text-sm text-gray-600 mt-4 mb-4">
            Maintenance operations for cleaning up stale data. Use with caution.
          </p>

          <!-- Cleanup Buttons -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <!-- Run All -->
            <button
              :disabled="!!cleanupLoading"
              class="btn-primary py-2 px-3 text-sm disabled:opacity-50 flex items-center justify-center gap-2"
              @click="runCleanup('all')"
            >
              <span v-if="cleanupLoading === 'all'" class="animate-spin" aria-hidden="true"
                >⏳</span
              >
              <span v-else aria-hidden="true">🔄</span>
              Run All
            </button>

            <!-- Archive Stale -->
            <button
              :disabled="!!cleanupLoading"
              class="btn-secondary py-2 px-3 text-sm disabled:opacity-50 flex items-center justify-center gap-2"
              title="Archive books stuck in EVALUATING for 30+ days"
              @click="runCleanup('stale')"
            >
              <span v-if="cleanupLoading === 'stale'" class="animate-spin" aria-hidden="true"
                >⏳</span
              >
              <span v-else aria-hidden="true">📦</span>
              Archive Stale
            </button>

            <!-- Check Expired -->
            <button
              :disabled="!!cleanupLoading"
              class="btn-secondary py-2 px-3 text-sm disabled:opacity-50 flex items-center justify-center gap-2"
              title="Check source URLs and mark expired ones"
              @click="runCleanup('expired')"
            >
              <span v-if="cleanupLoading === 'expired'" class="animate-spin" aria-hidden="true"
                >⏳</span
              >
              <span v-else aria-hidden="true">🔗</span>
              Check Sources
            </button>

            <!-- Retry Archives -->
            <button
              :disabled="!!cleanupLoading"
              class="btn-secondary py-2 px-3 text-sm disabled:opacity-50 flex items-center justify-center gap-2"
              title="Retry failed Wayback archives"
              @click="runCleanup('archives')"
            >
              <span v-if="cleanupLoading === 'archives'" class="animate-spin" aria-hidden="true"
                >⏳</span
              >
              <span v-else aria-hidden="true">🗄️</span>
              Retry Archives
            </button>
          </div>

          <!-- Orphan Images Section -->
          <OrphanCleanupPanel class="mt-4" />

          <!-- Results Display -->
          <div
            v-if="cleanupResult"
            class="mt-4 p-4 bg-[var(--color-status-success-bg)] border border-[var(--color-status-success-border)] rounded-lg"
          >
            <h4 class="text-sm font-medium text-[var(--color-status-success-text)] mb-2">
              Cleanup Results
            </h4>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div v-if="cleanupResult.stale_archived !== undefined">
                <span class="text-gray-600">Stale Archived:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.stale_archived }}</span>
              </div>
              <div v-if="cleanupResult.sources_checked !== undefined">
                <span class="text-gray-600">Sources Checked:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.sources_checked }}</span>
              </div>
              <div v-if="cleanupResult.sources_expired !== undefined">
                <span class="text-gray-600">Sources Expired:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.sources_expired }}</span>
              </div>
              <div v-if="cleanupResult.orphans_found !== undefined">
                <span class="text-gray-600">Orphans Found:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.orphans_found }}</span>
              </div>
              <div v-if="cleanupResult.orphans_deleted !== undefined">
                <span class="text-gray-600">Orphans Deleted:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.orphans_deleted }}</span>
              </div>
              <div v-if="cleanupResult.archives_retried !== undefined">
                <span class="text-gray-600">Archives Retried:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.archives_retried }}</span>
              </div>
              <div v-if="cleanupResult.archives_succeeded !== undefined">
                <span class="text-gray-600">Archives Succeeded:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.archives_succeeded }}</span>
              </div>
              <div v-if="cleanupResult.archives_failed !== undefined">
                <span class="text-gray-600">Archives Failed:</span>
                <span class="ml-1 font-medium">{{ cleanupResult.archives_failed }}</span>
              </div>
            </div>
          </div>

          <!-- Error Display -->
          <div
            v-if="cleanupError"
            class="mt-4 p-4 bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] rounded-lg"
          >
            <p class="text-sm text-[var(--color-status-error-text)]">{{ cleanupError }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Entity Form Modal -->
    <EntityFormModal
      :visible="formModal.visible"
      :entity-type="formModal.entityType"
      :entity="formModal.entity"
      :saving="formModal.saving"
      :error="formModal.error"
      @close="closeFormModal"
      @save="(data) => handleFormSave(formModal.entityType, data)"
    />

    <!-- Reassign Delete Modal -->
    <ReassignDeleteModal
      :visible="deleteModal.visible"
      :entity="deleteModal.entity"
      :all-entities="getEntitiesByType(deleteModal.entityType)"
      :entity-label="getEntityLabel(deleteModal.entityType)"
      :processing="deleteModal.processing"
      :error="deleteModal.error"
      @close="closeDeleteModal"
      @delete-direct="handleDeleteDirect(deleteModal.entityType)"
      @reassign-delete="(targetId) => handleReassignDelete(deleteModal.entityType, targetId)"
    />
  </div>
</template>
