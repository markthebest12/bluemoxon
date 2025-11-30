import { ref } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";

export interface Author {
  id: number;
  name: string;
}

export interface Publisher {
  id: number;
  name: string;
  tier: string | null;
  book_count: number;
}

export interface Binder {
  id: number;
  name: string;
  full_name: string | null;
  authentication_markers: string | null;
  book_count: number;
}

export const useReferencesStore = defineStore("references", () => {
  const authors = ref<Author[]>([]);
  const publishers = ref<Publisher[]>([]);
  const binders = ref<Binder[]>([]);
  const loading = ref(false);

  async function fetchAuthors() {
    try {
      const response = await api.get("/authors");
      authors.value = response.data;
    } catch {
      console.error("Failed to fetch authors");
    }
  }

  async function fetchPublishers() {
    try {
      const response = await api.get("/publishers");
      publishers.value = response.data;
    } catch {
      console.error("Failed to fetch publishers");
    }
  }

  async function fetchBinders() {
    try {
      const response = await api.get("/binders");
      binders.value = response.data;
    } catch {
      console.error("Failed to fetch binders");
    }
  }

  async function fetchAll() {
    loading.value = true;
    await Promise.all([fetchAuthors(), fetchPublishers(), fetchBinders()]);
    loading.value = false;
  }

  return {
    authors,
    publishers,
    binders,
    loading,
    fetchAuthors,
    fetchPublishers,
    fetchBinders,
    fetchAll,
  };
});
