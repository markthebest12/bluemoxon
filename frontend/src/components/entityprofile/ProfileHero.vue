<script setup lang="ts">
import { computed } from "vue";
import type { ProfileEntity, ProfileData } from "@/types/entityProfile";
import { formatTier } from "@/utils/socialCircles/formatters";
import { getToneStyle } from "@/composables/entityprofile/useToneStyle";

const props = defineProps<{
  entity: ProfileEntity;
  profile: ProfileData | null;
}>();

const dateDisplay = computed(() => {
  if (props.entity.birth_year && props.entity.death_year) {
    return `${props.entity.birth_year} \u2013 ${props.entity.death_year}`;
  }
  if (props.entity.founded_year) {
    return `Est. ${props.entity.founded_year}`;
  }
  return null;
});

const heroStories = computed(() => {
  if (!props.profile?.personal_stories) return [];
  return props.profile.personal_stories.filter((s) => s.display_in.includes("hero-bio"));
});
</script>

<template>
  <section class="profile-hero" :class="`profile-hero--${entity.type}`">
    <div class="profile-hero__info">
      <h1 class="profile-hero__name">{{ entity.name }}</h1>
      <div class="profile-hero__meta">
        <span v-if="entity.tier" class="profile-hero__tier">{{
          formatTier(entity.tier).label
        }}</span>
        <span v-if="entity.era" class="profile-hero__era">{{ entity.era }}</span>
        <span v-if="dateDisplay" class="profile-hero__dates">{{ dateDisplay }}</span>
      </div>

      <p v-if="profile?.bio_summary" class="profile-hero__bio">
        {{ profile.bio_summary }}
      </p>
      <p v-else class="profile-hero__bio profile-hero__bio--placeholder">
        Biographical summary not yet generated.
      </p>

      <div v-if="heroStories.length > 0" class="profile-hero__stories">
        <div
          v-for="(story, i) in heroStories"
          :key="i"
          class="profile-hero__story"
          :style="{ borderLeftColor: getToneStyle(story.tone).color }"
        >
          <span v-if="story.year" class="profile-hero__story-year">{{ story.year }}</span>
          {{ story.text }}
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.profile-hero {
  padding: 32px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  border: 1px solid var(--color-border, #e8e4de);
}

.profile-hero__name {
  font-size: 28px;
  margin: 0 0 8px;
  color: var(--color-text, #2c2420);
}

.profile-hero__meta {
  display: flex;
  gap: 12px;
  font-size: 14px;
  color: var(--color-text-muted, #8b8579);
  margin-bottom: 16px;
}

.profile-hero__bio {
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text, #2c2420);
}

.profile-hero__bio--placeholder {
  font-style: italic;
  color: var(--color-text-muted, #8b8579);
}

.profile-hero__stories {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-hero__story {
  padding: 12px 16px;
  background: var(--color-background, #fff);
  border-left: 3px solid var(--color-accent-gold, #b8860b);
  border-radius: 0 4px 4px 0;
  font-size: 14px;
  line-height: 1.5;
}

.profile-hero__story-year {
  font-weight: 600;
  margin-right: 8px;
}

@media (max-width: 768px) {
  .profile-hero {
    padding: 20px;
  }

  .profile-hero__name {
    font-size: 22px;
  }

  .profile-hero__bio {
    font-size: 15px;
  }
}
</style>
