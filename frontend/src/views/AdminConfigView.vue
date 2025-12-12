<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/services/api";

const config = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 });
const saving = ref(false);
const message = ref("");

onMounted(async () => {
  await loadConfig();
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
  message.value = "";
  try {
    await api.put("/admin/config", config.value);
    message.value = "Saved successfully";
    setTimeout(() => {
      message.value = "";
    }, 3000);
  } catch (e) {
    message.value = "Failed to save";
    console.error("Failed to save config:", e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto p-6">
    <h1 class="text-2xl font-bold mb-6">Admin Configuration</h1>
    <div class="bg-white rounded-lg shadow p-6 space-y-4">
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
        <span v-if="message" class="text-sm text-green-600">{{ message }}</span>
      </div>
    </div>
  </div>
</template>
