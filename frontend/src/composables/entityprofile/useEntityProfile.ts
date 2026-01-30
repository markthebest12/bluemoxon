/**
 * Main data fetcher and orchestrator for entity profiles.
 * Fetches profile data from the backend API and exposes reactive computed properties.
 */

import { computed, ref, shallowRef } from "vue";
import { api } from "@/services/api";
import type { EntityProfileResponse, ProfileConnection } from "@/types/entityProfile";

export type LoadingState = "idle" | "loading" | "loaded" | "error";

export function useEntityProfile() {
  const profileData = shallowRef<EntityProfileResponse | null>(null);
  const loadingState = ref<LoadingState>("idle");
  const error = ref<string | null>(null);
  const isRegenerating = ref(false);

  const isLoading = computed(() => loadingState.value === "loading");
  const hasError = computed(() => loadingState.value === "error");
  const entity = computed(() => profileData.value?.entity ?? null);
  const profile = computed(() => profileData.value?.profile ?? null);
  const connections = computed(() => profileData.value?.connections ?? []);
  const keyConnections = computed(() =>
    connections.value.filter((c: ProfileConnection) => c.is_key)
  );
  const otherConnections = computed(() =>
    connections.value.filter((c: ProfileConnection) => !c.is_key)
  );
  const books = computed(() => profileData.value?.books ?? []);
  const stats = computed(() => profileData.value?.stats ?? null);

  let abortController: AbortController | null = null;

  async function fetchProfile(entityType: string, entityId: number | string): Promise<void> {
    abortController?.abort();
    abortController = new AbortController();

    loadingState.value = "loading";
    error.value = null;

    try {
      const response = await api.get<EntityProfileResponse>(
        `/entity/${entityType}/${entityId}/profile`,
        { signal: abortController.signal }
      );

      profileData.value = response.data;
      loadingState.value = "loaded";
    } catch (e) {
      if (e instanceof Error && e.name === "CanceledError") {
        return;
      }
      error.value = e instanceof Error ? e.message : "Unknown error";
      loadingState.value = "error";
    }
  }

  async function regenerateProfile(entityType: string, entityId: number | string): Promise<void> {
    if (isRegenerating.value) return;
    isRegenerating.value = true;
    try {
      await api.post(`/entity/${entityType}/${entityId}/profile/regenerate`);
      await fetchProfile(entityType, entityId);
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Regeneration failed";
      loadingState.value = "error";
    } finally {
      isRegenerating.value = false;
    }
  }

  return {
    profileData,
    loadingState,
    error,
    isLoading,
    hasError,
    entity,
    profile,
    connections,
    keyConnections,
    otherConnections,
    books,
    stats,
    isRegenerating,
    fetchProfile,
    regenerateProfile,
  };
}
