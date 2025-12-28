<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { api } from "@/services/api";
import type { SystemInfoResponse, CostResponse } from "@/types/admin";

// Tab state
const activeTab = ref<"settings" | "status" | "scoring" | "tiers" | "costs">("settings");

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

async function fetchCostData() {
  loadingCost.value = true;
  costError.value = "";
  try {
    const res = await api.get("/admin/costs");
    costData.value = res.data;
  } catch (e) {
    costError.value = "Failed to load cost data";
    console.error("Failed to load cost data:", e);
  } finally {
    loadingCost.value = false;
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
      return "text-green-600";
    case "unhealthy":
      return "text-red-600";
    case "skipped":
      return "text-gray-400";
    default:
      return "text-yellow-600";
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

// Group entities by tier
const groupedAuthors = computed(() => groupByTier(systemInfo.value?.entity_tiers.authors || []));
const groupedPublishers = computed(() =>
  groupByTier(systemInfo.value?.entity_tiers.publishers || [])
);
const groupedBinders = computed(() => groupByTier(systemInfo.value?.entity_tiers.binders || []));

function groupByTier(entities: { name: string; tier: string }[]) {
  const groups: Record<string, string[]> = { TIER_1: [], TIER_2: [], TIER_3: [] };
  for (const e of entities) {
    if (groups[e.tier]) {
      groups[e.tier].push(e.name);
    }
  }
  return groups;
}

function formatTierLabel(tier: string) {
  return tier.replace("TIER_", "Tier ");
}

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
  const date = new Date(dateStr);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
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
      class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg"
    >
      <div class="flex items-center gap-2 text-red-700">
        <span class="text-xl">⚠️</span>
        <span class="font-medium">System health issues detected</span>
        <span class="text-sm text-red-600"> ({{ systemInfo.health.overall }}) </span>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="border-b border-gray-200 mb-6 overflow-x-auto">
      <nav class="-mb-px flex gap-4 sm:gap-8 min-w-max">
        <button
          @click="activeTab = 'settings'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'settings'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Settings
        </button>
        <button
          @click="activeTab = 'status'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'status'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          System Status
        </button>
        <button
          @click="activeTab = 'scoring'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'scoring'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Scoring Config
        </button>
        <button
          @click="activeTab = 'tiers'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'tiers'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Entity Tiers
        </button>
        <button
          @click="
            activeTab = 'costs';
            if (!costData) fetchCostData();
          "
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'costs'
              ? 'border-victorian-hunter-500 text-victorian-hunter-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Costs
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
        <button @click="saveConfig" :disabled="saving" class="btn-primary">
          {{ saving ? "Saving..." : "Save" }}
        </button>
        <span v-if="settingsMessage" class="text-sm text-green-600">{{ settingsMessage }}</span>
      </div>
    </div>

    <!-- System Status Tab -->
    <div v-else-if="activeTab === 'status'" class="flex flex-col gap-6">
      <div class="flex justify-end">
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-sm"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="infoError" class="p-4 bg-red-50 text-red-700 rounded-sm">
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
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-sm"
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

    <!-- Entity Tiers Tab -->
    <div v-else-if="activeTab === 'tiers'" class="flex flex-col gap-6">
      <div class="flex justify-end">
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-sm"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="systemInfo" class="grid md:grid-cols-3 gap-6">
        <!-- Authors -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Authors</h3>
          <div class="flex flex-col gap-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">
                {{ formatTierLabel(tier) }}
              </h4>
              <ul v-if="groupedAuthors[tier]?.length" class="flex flex-col gap-1 text-sm">
                <li v-for="name in groupedAuthors[tier]" :key="name">• {{ name }}</li>
              </ul>
              <p v-else class="text-sm text-gray-400 italic">None</p>
            </div>
          </div>
          <p class="mt-4 text-xs text-gray-400">
            {{ systemInfo.entity_tiers.authors.length }} total
          </p>
        </div>

        <!-- Publishers -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Publishers</h3>
          <div class="flex flex-col gap-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">
                {{ formatTierLabel(tier) }}
              </h4>
              <ul v-if="groupedPublishers[tier]?.length" class="flex flex-col gap-1 text-sm">
                <li v-for="name in groupedPublishers[tier]" :key="name">• {{ name }}</li>
              </ul>
              <p v-else class="text-sm text-gray-400 italic">None</p>
            </div>
          </div>
          <p class="mt-4 text-xs text-gray-400">
            {{ systemInfo.entity_tiers.publishers.length }} total
          </p>
        </div>

        <!-- Binders -->
        <div class="bg-white rounded-lg shadow-sm p-6">
          <h3 class="text-lg font-semibold mb-4">Binders</h3>
          <div class="flex flex-col gap-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">
                {{ formatTierLabel(tier) }}
              </h4>
              <ul v-if="groupedBinders[tier]?.length" class="flex flex-col gap-1 text-sm">
                <li v-for="name in groupedBinders[tier]" :key="name">• {{ name }}</li>
              </ul>
              <p v-else class="text-sm text-gray-400 italic">None</p>
            </div>
          </div>
          <p class="mt-4 text-xs text-gray-400">
            {{ systemInfo.entity_tiers.binders.length }} total
          </p>
        </div>
      </div>
    </div>

    <!-- Costs Tab -->
    <div v-else-if="activeTab === 'costs'" class="flex flex-col gap-6">
      <div class="flex justify-end">
        <button
          @click="fetchCostData"
          :disabled="loadingCost"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-sm"
        >
          {{ loadingCost ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="costError" class="p-4 bg-red-50 text-red-700 rounded-sm">
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
          <h3 class="text-lg font-semibold mb-4">Daily Trend (Last 14 Days)</h3>
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
  </div>
</template>
