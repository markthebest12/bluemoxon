<template>
  <div class="profile-skeleton" aria-busy="true" aria-label="Loading profile">
    <div class="profile-skeleton__hero">
      <div class="profile-skeleton__line profile-skeleton__line--title" />
      <div class="profile-skeleton__line profile-skeleton__line--meta" />
      <div class="profile-skeleton__line profile-skeleton__line--bio" />
      <div class="profile-skeleton__line profile-skeleton__line--bio" />
    </div>
    <div class="profile-skeleton__content">
      <div class="profile-skeleton__block" />
      <div class="profile-skeleton__block" />
    </div>
  </div>
</template>

<style scoped>
.profile-skeleton__hero {
  padding: 32px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  margin-bottom: 24px;
}

.profile-skeleton__line {
  background: var(--color-border, #e8e4de);
  border-radius: 4px;
  animation: pulse 1.5s ease-in-out infinite;
}

.profile-skeleton__line--title {
  width: 40%;
  height: 28px;
  margin-bottom: 12px;
}

.profile-skeleton__line--meta {
  width: 30%;
  height: 14px;
  margin-bottom: 16px;
}

.profile-skeleton__line--bio {
  width: 90%;
  height: 14px;
  margin-bottom: 8px;
}

.profile-skeleton__content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.profile-skeleton__block {
  height: 200px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 1024px) {
  .profile-skeleton__content {
    grid-template-columns: 1fr;
  }
}
</style>
