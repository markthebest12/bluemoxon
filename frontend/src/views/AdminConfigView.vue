<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { api } from "@/services/api";
import type { SystemInfoResponse } from "@/types/admin";

// Tab state
const activeTab = ref<"settings" | "status" | "scoring" | "tiers">("settings");

// Settings tab (existing functionality)
const config = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 });
const saving = ref(false);
const settingsMessage = ref("");

// System info (for other tabs)
const systemInfo = ref<SystemInfoResponse | null>(null);
const loadingInfo = ref(false);
const infoError = ref("");

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
    <div class="border-b border-gray-200 mb-6">
      <nav class="-mb-px flex space-x-8">
        <button
          @click="activeTab = 'settings'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'settings'
              ? 'border-blue-500 text-blue-600'
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
              ? 'border-blue-500 text-blue-600'
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
              ? 'border-blue-500 text-blue-600'
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
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Entity Tiers
        </button>
      </nav>
    </div>

    <!-- Settings Tab -->
    <div v-if="activeTab === 'settings'" class="bg-white rounded-lg shadow p-6 space-y-4">
      <h2 class="text-lg font-semibold">Currency Conversion Rates</h2>
      <div class="grid grid-cols-2 gap-4">
        <label class="block">
          <span class="text-sm text-gray-700">GBP to USD</span>
          <input
            v-model.number="config.gbp_to_usd_rate"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded border-gray-300 shadow-sm"
          />
        </label>
        <label class="block">
          <span class="text-sm text-gray-700">EUR to USD</span>
          <input
            v-model.number="config.eur_to_usd_rate"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded border-gray-300 shadow-sm"
          />
        </label>
      </div>
      <div class="flex items-center gap-4">
        <button
          @click="saveConfig"
          :disabled="saving"
          class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {{ saving ? "Saving..." : "Save" }}
        </button>
        <span v-if="settingsMessage" class="text-sm text-green-600">{{ settingsMessage }}</span>
      </div>
    </div>

    <!-- System Status Tab -->
    <div v-else-if="activeTab === 'status'" class="space-y-6">
      <div class="flex justify-end">
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="infoError" class="p-4 bg-red-50 text-red-700 rounded">
        {{ infoError }}
      </div>

      <div v-else-if="systemInfo" class="space-y-6">
        <!-- Version & Deployment -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Version & Deployment</h3>
          <dl class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt class="text-gray-500">App Version</dt>
              <dd class="font-mono">{{ systemInfo.system.version }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Git SHA</dt>
              <dd class="font-mono">{{ systemInfo.system.git_sha || "N/A" }}</dd>
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Health Checks</h3>
          <div class="space-y-3">
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Bedrock Models</h3>
          <dl class="space-y-3 text-sm">
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
      </div>
    </div>

    <!-- Scoring Config Tab -->
    <div v-else-if="activeTab === 'scoring'" class="space-y-6">
      <div class="flex justify-between items-center">
        <p class="text-sm text-gray-500">★ = Key tunable</p>
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="systemInfo" class="grid md:grid-cols-2 gap-6">
        <!-- Quality Points -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Quality Score Points</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.quality_points"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(String(key)) }"
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Strategic Fit Points</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.strategic_points"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(String(key)) }"
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Thresholds</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.thresholds"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(String(key)) }"
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Combined Score Weights</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.weights"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(String(key)) }"
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Offer Discounts</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.offer_discounts"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(String(key)) }"
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Era Boundaries</h3>
          <dl class="space-y-1 text-sm">
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
    <div v-else-if="activeTab === 'tiers'" class="space-y-6">
      <div class="flex justify-end">
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="systemInfo" class="grid md:grid-cols-3 gap-6">
        <!-- Authors -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Authors</h3>
          <div class="space-y-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">
                {{ formatTierLabel(tier) }}
              </h4>
              <ul v-if="groupedAuthors[tier]?.length" class="space-y-1 text-sm">
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Publishers</h3>
          <div class="space-y-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">
                {{ formatTierLabel(tier) }}
              </h4>
              <ul v-if="groupedPublishers[tier]?.length" class="space-y-1 text-sm">
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
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Binders</h3>
          <div class="space-y-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">
                {{ formatTierLabel(tier) }}
              </h4>
              <ul v-if="groupedBinders[tier]?.length" class="space-y-1 text-sm">
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
  </div>
</template>
