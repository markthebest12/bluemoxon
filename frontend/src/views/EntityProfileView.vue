<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useEntityProfile } from "@/composables/entityprofile";
import ProfileHero from "@/components/entityprofile/ProfileHero.vue";
import KeyConnections from "@/components/entityprofile/KeyConnections.vue";
import AllConnections from "@/components/entityprofile/AllConnections.vue";
import EntityBooks from "@/components/entityprofile/EntityBooks.vue";
import CollectionStats from "@/components/entityprofile/CollectionStats.vue";
import ProfileSkeleton from "@/components/entityprofile/ProfileSkeleton.vue";
import StaleProfileBanner from "@/components/entityprofile/StaleProfileBanner.vue";
import EgoNetwork from "@/components/entityprofile/EgoNetwork.vue";

const props = defineProps<{
  type: string;
  id: string;
}>();

const route = useRoute();
const {
  entity,
  profile,
  connections,
  keyConnections,
  otherConnections,
  books,
  stats,
  isLoading,
  hasError,
  error,
  fetchProfile,
  regenerateProfile,
} = useEntityProfile();

onMounted(() => {
  void fetchProfile(props.type, props.id);
});

// Refetch when route params change (navigating between profiles)
watch(
  () => route.params,
  (newParams) => {
    if (newParams.type && newParams.id) {
      void fetchProfile(newParams.type as string, newParams.id as string);
    }
  }
);
</script>

<template>
  <div class="entity-profile-view">
    <nav class="entity-profile-view__nav">
      <router-link to="/social-circles" class="entity-profile-view__back">
        &larr; Back to Social Circles
      </router-link>
    </nav>

    <ProfileSkeleton v-if="isLoading" />

    <div v-else-if="hasError" class="entity-profile-view__error">
      <p>Failed to load profile: {{ error }}</p>
      <button @click="fetchProfile(props.type, props.id)">Retry</button>
    </div>

    <template v-else-if="entity">
      <StaleProfileBanner
        v-if="profile?.is_stale"
        :entity-type="entity.type"
        :entity-id="entity.id"
        @regenerate="regenerateProfile(entity.type, entity.id)"
      />

      <ProfileHero :entity="entity" :profile="profile" />

      <EgoNetwork
        v-if="connections.length > 0"
        :entity-id="entity.id"
        :entity-type="entity.type"
        :entity-name="entity.name"
        :connections="connections"
      />

      <div class="entity-profile-view__content">
        <div class="entity-profile-view__left">
          <KeyConnections v-if="keyConnections.length > 0" :connections="keyConnections" />
          <AllConnections v-if="otherConnections.length > 0" :connections="otherConnections" />
        </div>

        <div class="entity-profile-view__right">
          <EntityBooks :books="books" />
          <CollectionStats v-if="stats" :stats="stats" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.entity-profile-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.entity-profile-view__nav {
  margin-bottom: 24px;
}

.entity-profile-view__back {
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
  font-size: 14px;
}

.entity-profile-view__back:hover {
  text-decoration: underline;
}

.entity-profile-view__error {
  text-align: center;
  padding: 48px;
  color: var(--color-danger, #dc3545);
}

.entity-profile-view__content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-top: 24px;
}

.entity-profile-view__left,
.entity-profile-view__right {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 1024px) {
  .entity-profile-view__content {
    grid-template-columns: 1fr;
  }
}
</style>
