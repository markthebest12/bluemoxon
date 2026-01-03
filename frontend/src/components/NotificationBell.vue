<script setup lang="ts">
import { ref, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { api } from "@/services/api";

interface Notification {
  id: number;
  title: string;
  message: string;
  read: boolean;
  created_at?: string;
  notification_type?: string;
  book_id?: number;
}

interface NotificationsResponse {
  notifications: Notification[];
  unread_count: number;
}

const notifications = ref<Notification[]>([]);
const unreadCount = ref(0);
const isOpen = ref(false);
const loading = ref(false);

async function fetchNotifications() {
  loading.value = true;
  try {
    const response = await api.get<NotificationsResponse>("/users/me/notifications");
    notifications.value = response.data.notifications;
    unreadCount.value = response.data.unread_count;
  } catch (e) {
    console.error("Failed to fetch notifications:", e);
  } finally {
    loading.value = false;
  }
}

async function markAsRead(notification: Notification) {
  if (notification.read) return;

  try {
    await api.post(`/users/me/notifications/${notification.id}/read`);
    notification.read = true;
    unreadCount.value = Math.max(0, unreadCount.value - 1);
  } catch (e) {
    console.error("Failed to mark notification as read:", e);
  }
}

function toggleDropdown() {
  isOpen.value = !isOpen.value;
}

function closeDropdown() {
  isOpen.value = false;
}

onMounted(() => {
  void fetchNotifications();
});
</script>

<template>
  <div class="relative">
    <!-- Bell Button -->
    <button
      @click="toggleDropdown"
      class="relative p-2 text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors"
      aria-label="Notifications"
    >
      <!-- Bell Icon -->
      <svg
        class="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>

      <!-- Unread Badge -->
      <span
        v-if="unreadCount > 0"
        data-testid="notification-badge"
        class="absolute top-0 right-0 inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-500 rounded-full transform translate-x-1 -translate-y-1"
      >
        {{ unreadCount > 99 ? "99+" : unreadCount }}
      </span>
    </button>

    <!-- Overlay for closing dropdown -->
    <div
      v-if="isOpen"
      data-testid="notification-overlay"
      class="fixed inset-0 z-40"
      @click="closeDropdown"
    />

    <!-- Dropdown -->
    <Transition
      enter-from-class="opacity-0 scale-95"
      enter-active-class="transition duration-100 ease-out"
      enter-to-class="opacity-100 scale-100"
      leave-from-class="opacity-100 scale-100"
      leave-active-class="transition duration-75 ease-in"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="isOpen"
        data-testid="notification-dropdown"
        class="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto rounded-lg shadow-lg z-50 bg-[var(--color-surface-elevated)]"
      >
        <!-- Header -->
        <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-sm font-semibold text-[var(--color-text-primary)]">Notifications</h3>
        </div>

        <!-- Notifications List -->
        <div class="divide-y divide-gray-100 dark:divide-gray-700">
          <template v-if="notifications.length > 0">
            <div
              v-for="notification in notifications"
              :key="notification.id"
              :data-testid="`notification-item-${notification.id}`"
              @click="markAsRead(notification)"
              :class="[
                'px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors',
                !notification.read ? 'bg-blue-50 dark:bg-blue-900/20' : '',
              ]"
            >
              <div class="flex items-start gap-3">
                <!-- Unread indicator -->
                <div
                  v-if="!notification.read"
                  class="mt-1.5 w-2 h-2 rounded-full bg-blue-500 flex-shrink-0"
                />
                <div :class="notification.read ? 'ml-5' : ''">
                  <p class="text-sm font-medium text-[var(--color-text-primary)]">
                    {{ notification.title }}
                  </p>
                  <p class="text-sm text-[var(--color-text-secondary)] mt-0.5">
                    {{ notification.message }}
                  </p>
                </div>
              </div>
            </div>
          </template>

          <!-- Empty State -->
          <div
            v-else
            class="px-4 py-8 text-center text-[var(--color-text-secondary)]"
          >
            <svg
              class="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            <p class="text-sm">No notifications</p>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <RouterLink
            to="/notifications"
            data-testid="view-all-link"
            class="block text-center text-sm font-medium text-victorian-hunter-600 hover:text-victorian-hunter-800 dark:text-victorian-gold-light dark:hover:text-victorian-gold transition-colors"
            @click="closeDropdown"
          >
            View All Notifications
          </RouterLink>
        </div>
      </div>
    </Transition>
  </div>
</template>
