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

  async function fetchProfile(entityType: string, entityId: number | string): Promise<void> {
    loadingState.value = "loading";
    error.value = null;

    try {
      const response = await api.get<EntityProfileResponse>(
        `/entity/${entityType}/${entityId}/profile`
      );

      profileData.value = response.data;
      loadingState.value = "loaded";
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Unknown error";
      loadingState.value = "error";
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
    fetchProfile,
  };
}
