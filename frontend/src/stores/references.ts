import { ref } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";
import { handleApiError } from "@/utils/errorHandler";

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
    } catch (e) {
      handleApiError(e, "Loading authors");
    }
  }

  async function fetchPublishers() {
    try {
      const response = await api.get("/publishers");
      publishers.value = response.data;
    } catch (e) {
      handleApiError(e, "Loading publishers");
    }
  }

  async function fetchBinders() {
    try {
      const response = await api.get("/binders");
      binders.value = response.data;
    } catch (e) {
      handleApiError(e, "Loading binders");
    }
  }

  async function fetchAll() {
    loading.value = true;
    await Promise.all([fetchAuthors(), fetchPublishers(), fetchBinders()]);
    loading.value = false;
  }

  async function createAuthor(name: string): Promise<Author> {
    const response = await api.post("/authors", { name: name.trim() });
    authors.value.push(response.data);
    return response.data;
  }

  async function createPublisher(name: string): Promise<Publisher> {
    const response = await api.post("/publishers", { name: name.trim() });
    publishers.value.push(response.data);
    return response.data;
  }

  async function createBinder(name: string): Promise<Binder> {
    const response = await api.post("/binders", { name: name.trim() });
    binders.value.push(response.data);
    return response.data;
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
    createAuthor,
    createPublisher,
    createBinder,
  };
});
