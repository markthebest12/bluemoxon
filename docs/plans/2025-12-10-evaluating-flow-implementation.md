# Evaluating Flow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a modal to the Acquisitions dashboard for quickly adding books to the watchlist (EVALUATING status).

**Architecture:** New `AddToWatchlistModal.vue` component triggered from AcquisitionsView. Reusable `ComboboxWithAdd.vue` for author/publisher/binder selection with inline creation. Store action calls `POST /books` with `status: EVALUATING`.

**Tech Stack:** Vue 3, TypeScript, Pinia, Tailwind CSS

---

## Task 1: Add `addToWatchlist` action to acquisitions store

**Files:**
- Modify: `frontend/src/stores/acquisitions.ts`
- Test: `frontend/src/stores/__tests__/acquisitions.spec.ts`

**Step 1: Write the failing test**

Add to `frontend/src/stores/__tests__/acquisitions.spec.ts` at the end of the describe block:

```typescript
describe("addToWatchlist", () => {
  it("creates book with EVALUATING status and adds to evaluating list", async () => {
    const store = useAcquisitionsStore();
    const mockBook = {
      id: 999,
      title: "Test Book",
      status: "EVALUATING",
      author: { id: 1, name: "Test Author" },
    };
    vi.mocked(api.post).mockResolvedValueOnce({ data: mockBook });

    const payload = {
      title: "Test Book",
      author_id: 1,
      status: "EVALUATING",
    };
    const result = await store.addToWatchlist(payload);

    expect(api.post).toHaveBeenCalledWith("/books", payload);
    expect(result).toEqual(mockBook);
    expect(store.evaluating).toContainEqual(mockBook);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run -t "addToWatchlist"`

Expected: FAIL with "store.addToWatchlist is not a function"

**Step 3: Write minimal implementation**

Add to `frontend/src/stores/acquisitions.ts` before the return statement:

```typescript
export interface WatchlistPayload {
  title: string;
  author_id: number;
  publisher_id?: number;
  binder_id?: number;
  publication_date?: string;
  volumes?: number;
  source_url?: string;
  purchase_price?: number; // This is the asking price for watchlist items
}

// Add inside the store, before return statement:
async function addToWatchlist(payload: WatchlistPayload) {
  const fullPayload = {
    ...payload,
    status: "EVALUATING",
    inventory_type: "PRIMARY",
  };
  const response = await api.post("/books", fullPayload);
  evaluating.value.unshift(response.data);
  return response.data;
}
```

Update the return statement to include `addToWatchlist`:

```typescript
return {
  // ... existing
  addToWatchlist,
};
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run -t "addToWatchlist"`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/stores/acquisitions.ts frontend/src/stores/__tests__/acquisitions.spec.ts
git commit -m "feat: add addToWatchlist action to acquisitions store"
```

---

## Task 2: Add create actions to references store

**Files:**
- Modify: `frontend/src/stores/references.ts`
- Test: `frontend/src/stores/__tests__/references.spec.ts` (create if needed)

**Step 1: Write the failing test**

Create `frontend/src/stores/__tests__/references.spec.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useReferencesStore } from "../references";
import { api } from "@/services/api";

vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("references store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("createAuthor", () => {
    it("creates author and adds to list", async () => {
      const store = useReferencesStore();
      const mockAuthor = { id: 100, name: "New Author" };
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockAuthor });

      const result = await store.createAuthor("New Author");

      expect(api.post).toHaveBeenCalledWith("/authors", { name: "New Author" });
      expect(result).toEqual(mockAuthor);
      expect(store.authors).toContainEqual(mockAuthor);
    });
  });

  describe("createPublisher", () => {
    it("creates publisher and adds to list", async () => {
      const store = useReferencesStore();
      const mockPublisher = { id: 100, name: "New Publisher", tier: null, book_count: 0 };
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockPublisher });

      const result = await store.createPublisher("New Publisher");

      expect(api.post).toHaveBeenCalledWith("/publishers", { name: "New Publisher" });
      expect(result).toEqual(mockPublisher);
      expect(store.publishers).toContainEqual(mockPublisher);
    });
  });

  describe("createBinder", () => {
    it("creates binder and adds to list", async () => {
      const store = useReferencesStore();
      const mockBinder = { id: 100, name: "New Binder", full_name: null, authentication_markers: null, book_count: 0 };
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockBinder });

      const result = await store.createBinder("New Binder");

      expect(api.post).toHaveBeenCalledWith("/binders", { name: "New Binder" });
      expect(result).toEqual(mockBinder);
      expect(store.binders).toContainEqual(mockBinder);
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run references.spec.ts`

Expected: FAIL with "store.createAuthor is not a function"

**Step 3: Write minimal implementation**

Add to `frontend/src/stores/references.ts` before the return statement:

```typescript
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
```

Update the return statement:

```typescript
return {
  // ... existing
  createAuthor,
  createPublisher,
  createBinder,
};
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run references.spec.ts`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/stores/references.ts frontend/src/stores/__tests__/references.spec.ts
git commit -m "feat: add create actions for authors, publishers, binders"
```

---

## Task 3: Create ComboboxWithAdd component

**Files:**
- Create: `frontend/src/components/ComboboxWithAdd.vue`
- Test: `frontend/src/components/__tests__/ComboboxWithAdd.spec.ts`

**Step 1: Write the failing test**

Create `frontend/src/components/__tests__/ComboboxWithAdd.spec.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ComboboxWithAdd from "../ComboboxWithAdd.vue";

describe("ComboboxWithAdd", () => {
  const options = [
    { id: 1, name: "Option A" },
    { id: 2, name: "Option B" },
  ];

  it("renders with label", () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    expect(wrapper.text()).toContain("Author");
  });

  it("filters options as user types", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.setValue("Option A");
    // Should show filtered option
    expect(wrapper.text()).toContain("Option A");
    expect(wrapper.text()).not.toContain("Option B");
  });

  it("shows add new option when no match", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.setValue("New Name");
    expect(wrapper.text()).toContain('+ Add "New Name"');
  });

  it("emits update:modelValue when option selected", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.trigger("focus");
    const optionButtons = wrapper.findAll('[data-testid="option"]');
    await optionButtons[0].trigger("click");
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")![0]).toEqual([1]);
  });

  it("emits create when add new clicked", async () => {
    const wrapper = mount(ComboboxWithAdd, {
      props: {
        label: "Author",
        options,
        modelValue: null,
      },
    });
    const input = wrapper.find("input");
    await input.setValue("Brand New");
    const addButton = wrapper.find('[data-testid="add-new"]');
    await addButton.trigger("click");
    expect(wrapper.emitted("create")).toBeTruthy();
    expect(wrapper.emitted("create")![0]).toEqual(["Brand New"]);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run ComboboxWithAdd.spec.ts`

Expected: FAIL with "Cannot find module '../ComboboxWithAdd.vue'"

**Step 3: Write minimal implementation**

Create `frontend/src/components/ComboboxWithAdd.vue`:

```vue
<script setup lang="ts">
import { ref, computed, watch } from "vue";

interface Option {
  id: number;
  name: string;
}

const props = defineProps<{
  label: string;
  options: Option[];
  modelValue: number | null;
  placeholder?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number | null];
  create: [name: string];
}>();

const searchText = ref("");
const isOpen = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);

// Find selected option to display
const selectedOption = computed(() => {
  if (!props.modelValue) return null;
  return props.options.find((o) => o.id === props.modelValue);
});

// Filter options based on search
const filteredOptions = computed(() => {
  if (!searchText.value) return props.options;
  const search = searchText.value.toLowerCase();
  return props.options.filter((o) => o.name.toLowerCase().includes(search));
});

// Show "add new" if search doesn't match any option exactly
const showAddNew = computed(() => {
  if (!searchText.value.trim()) return false;
  const search = searchText.value.toLowerCase().trim();
  return !props.options.some((o) => o.name.toLowerCase() === search);
});

// Update display when modelValue changes
watch(
  () => props.modelValue,
  () => {
    if (selectedOption.value) {
      searchText.value = selectedOption.value.name;
    }
  },
  { immediate: true }
);

function handleFocus() {
  isOpen.value = true;
  searchText.value = "";
}

function handleBlur() {
  // Delay to allow click events to fire
  setTimeout(() => {
    isOpen.value = false;
    if (selectedOption.value) {
      searchText.value = selectedOption.value.name;
    }
  }, 200);
}

function selectOption(option: Option) {
  emit("update:modelValue", option.id);
  searchText.value = option.name;
  isOpen.value = false;
}

function handleAddNew() {
  const name = searchText.value.trim();
  if (name) {
    emit("create", name);
  }
}
</script>

<template>
  <div class="relative">
    <label class="block text-sm font-medium text-gray-700 mb-1">
      {{ label }}
    </label>
    <input
      ref="inputRef"
      v-model="searchText"
      type="text"
      :placeholder="placeholder || `Select or add ${label.toLowerCase()}`"
      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      @focus="handleFocus"
      @blur="handleBlur"
    />

    <!-- Dropdown -->
    <div
      v-if="isOpen"
      class="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto"
    >
      <!-- Filtered options -->
      <button
        v-for="option in filteredOptions"
        :key="option.id"
        type="button"
        data-testid="option"
        class="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
        @mousedown.prevent="selectOption(option)"
      >
        {{ option.name }}
      </button>

      <!-- Add new option -->
      <button
        v-if="showAddNew"
        type="button"
        data-testid="add-new"
        class="w-full px-3 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 border-t border-gray-200"
        @mousedown.prevent="handleAddNew"
      >
        + Add "{{ searchText.trim() }}"
      </button>

      <!-- Empty state -->
      <div
        v-if="filteredOptions.length === 0 && !showAddNew"
        class="px-3 py-2 text-sm text-gray-500"
      >
        No options found
      </div>
    </div>
  </div>
</template>
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run ComboboxWithAdd.spec.ts`

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add frontend/src/components/ComboboxWithAdd.vue frontend/src/components/__tests__/ComboboxWithAdd.spec.ts
git commit -m "feat: add ComboboxWithAdd component with inline creation"
```

---

## Task 4: Create AddToWatchlistModal component

**Files:**
- Create: `frontend/src/components/AddToWatchlistModal.vue`
- Test: `frontend/src/components/__tests__/AddToWatchlistModal.spec.ts`

**Step 1: Write the failing test**

Create `frontend/src/components/__tests__/AddToWatchlistModal.spec.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import AddToWatchlistModal from "../AddToWatchlistModal.vue";
import { useReferencesStore } from "@/stores/references";
import { useAcquisitionsStore } from "@/stores/acquisitions";

vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("AddToWatchlistModal", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("renders modal with form fields", () => {
    const wrapper = mount(AddToWatchlistModal, {
      global: {
        stubs: {
          Teleport: true,
        },
      },
    });
    expect(wrapper.text()).toContain("Add to Watchlist");
    expect(wrapper.text()).toContain("Title");
    expect(wrapper.text()).toContain("Author");
  });

  it("emits close when cancel clicked", async () => {
    const wrapper = mount(AddToWatchlistModal, {
      global: {
        stubs: {
          Teleport: true,
        },
      },
    });
    const cancelButton = wrapper.find('button[type="button"]');
    await cancelButton.trigger("click");
    expect(wrapper.emitted("close")).toBeTruthy();
  });

  it("validates required fields before submit", async () => {
    const wrapper = mount(AddToWatchlistModal, {
      global: {
        stubs: {
          Teleport: true,
        },
      },
    });
    const form = wrapper.find("form");
    await form.trigger("submit");
    expect(wrapper.text()).toContain("Title is required");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run AddToWatchlistModal.spec.ts`

Expected: FAIL with "Cannot find module '../AddToWatchlistModal.vue'"

**Step 3: Write minimal implementation**

Create `frontend/src/components/AddToWatchlistModal.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from "vue";
import { useReferencesStore } from "@/stores/references";
import { useAcquisitionsStore } from "@/stores/acquisitions";
import ComboboxWithAdd from "./ComboboxWithAdd.vue";

const emit = defineEmits<{
  close: [];
  added: [];
}>();

const refsStore = useReferencesStore();
const acquisitionsStore = useAcquisitionsStore();

const form = ref({
  title: "",
  author_id: null as number | null,
  publisher_id: null as number | null,
  binder_id: null as number | null,
  publication_date: "",
  volumes: 1,
  source_url: "",
  purchase_price: null as number | null, // Asking price
});

const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const validationErrors = ref<Record<string, string>>({});

// Lock body scroll when modal is open
watch(
  () => true,
  () => {
    document.body.style.overflow = "hidden";
  },
  { immediate: true }
);

onUnmounted(() => {
  document.body.style.overflow = "";
});

onMounted(() => {
  refsStore.fetchAll();
});

function validate(): boolean {
  validationErrors.value = {};

  if (!form.value.title.trim()) {
    validationErrors.value.title = "Title is required";
  }
  if (!form.value.author_id) {
    validationErrors.value.author = "Author is required";
  }

  return Object.keys(validationErrors.value).length === 0;
}

async function handleSubmit() {
  if (!validate()) return;

  submitting.value = true;
  errorMessage.value = null;

  try {
    const payload = {
      title: form.value.title.trim(),
      author_id: form.value.author_id!,
      publisher_id: form.value.publisher_id || undefined,
      binder_id: form.value.binder_id || undefined,
      publication_date: form.value.publication_date || undefined,
      volumes: form.value.volumes || 1,
      source_url: form.value.source_url || undefined,
      purchase_price: form.value.purchase_price || undefined,
    };

    await acquisitionsStore.addToWatchlist(payload);
    emit("added");
    emit("close");
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to add to watchlist";
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  if (!submitting.value) {
    emit("close");
  }
}

async function handleCreateAuthor(name: string) {
  try {
    const author = await refsStore.createAuthor(name);
    form.value.author_id = author.id;
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to create author";
  }
}

async function handleCreatePublisher(name: string) {
  try {
    const publisher = await refsStore.createPublisher(name);
    form.value.publisher_id = publisher.id;
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to create publisher";
  }
}

async function handleCreateBinder(name: string) {
  try {
    const binder = await refsStore.createBinder(name);
    form.value.binder_id = binder.id;
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to create binder";
  }
}

function openSourceUrl() {
  if (form.value.source_url) {
    window.open(form.value.source_url, "_blank");
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="handleClose"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Add to Watchlist</h2>
          <button
            @click="handleClose"
            :disabled="submitting"
            class="text-gray-500 hover:text-gray-700 disabled:opacity-50"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSubmit" class="p-4 space-y-4">
          <!-- Error Message -->
          <div
            v-if="errorMessage"
            class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm"
          >
            {{ errorMessage }}
          </div>

          <!-- Title -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Title <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.title"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :class="{ 'border-red-500': validationErrors.title }"
            />
            <p v-if="validationErrors.title" class="mt-1 text-sm text-red-500">
              {{ validationErrors.title }}
            </p>
          </div>

          <!-- Author & Publisher Row -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <ComboboxWithAdd
                label="Author"
                :options="refsStore.authors"
                v-model="form.author_id"
                @create="handleCreateAuthor"
              />
              <p v-if="validationErrors.author" class="mt-1 text-sm text-red-500">
                {{ validationErrors.author }}
              </p>
            </div>
            <ComboboxWithAdd
              label="Publisher"
              :options="refsStore.publishers"
              v-model="form.publisher_id"
              @create="handleCreatePublisher"
            />
          </div>

          <!-- Binder & Publication Date Row -->
          <div class="grid grid-cols-2 gap-4">
            <ComboboxWithAdd
              label="Binder"
              :options="refsStore.binders"
              v-model="form.binder_id"
              @create="handleCreateBinder"
            />
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Publication Date
              </label>
              <input
                v-model="form.publication_date"
                type="text"
                placeholder="1867"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          <!-- Volumes & Asking Price Row -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Volumes
              </label>
              <input
                v-model.number="form.volumes"
                type="number"
                min="1"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Asking Price
              </label>
              <div class="relative">
                <span class="absolute left-3 top-2 text-gray-500">$</span>
                <input
                  v-model.number="form.purchase_price"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="Optional"
                  class="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          <!-- Source URL -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Source URL
            </label>
            <div class="flex gap-2">
              <input
                v-model="form.source_url"
                type="url"
                placeholder="https://ebay.com/itm/..."
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                :disabled="!form.source_url"
                @click="openSourceUrl"
                class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Open URL"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- Footer Buttons -->
          <div class="flex gap-3 pt-4">
            <button
              type="button"
              @click="handleClose"
              :disabled="submitting"
              class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="submitting"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ submitting ? "Adding..." : "Add to List" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run AddToWatchlistModal.spec.ts`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add frontend/src/components/AddToWatchlistModal.vue frontend/src/components/__tests__/AddToWatchlistModal.spec.ts
git commit -m "feat: add AddToWatchlistModal component"
```

---

## Task 5: Wire up modal in AcquisitionsView

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue`
- Test: `frontend/src/views/__tests__/AcquisitionsView.spec.ts`

**Step 1: Write the failing test**

Add to `frontend/src/views/__tests__/AcquisitionsView.spec.ts`:

```typescript
it("opens AddToWatchlistModal when add button clicked", async () => {
  vi.mocked(api.get).mockImplementation((_url, config) => {
    const status = config?.params?.status;
    if (status === "EVALUATING") return Promise.resolve({ data: { items: [] } });
    if (status === "IN_TRANSIT") return Promise.resolve({ data: { items: [] } });
    return Promise.resolve({ data: { items: [] } });
  });

  const wrapper = mount(AcquisitionsView, {
    global: {
      plugins: [router, createPinia()],
      stubs: {
        Teleport: true,
      },
    },
  });

  await flushPromises();

  const addButton = wrapper.find('[data-testid="add-to-watchlist"]');
  await addButton.trigger("click");

  expect(wrapper.findComponent({ name: "AddToWatchlistModal" }).exists()).toBe(true);
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run AcquisitionsView.spec.ts`

Expected: FAIL with "Cannot find '[data-testid="add-to-watchlist"]'"

**Step 3: Write minimal implementation**

Modify `frontend/src/views/AcquisitionsView.vue`:

1. Add import at top of script:
```typescript
import AddToWatchlistModal from "@/components/AddToWatchlistModal.vue";
```

2. Add state for modal:
```typescript
const showWatchlistModal = ref(false);

function openWatchlistModal() {
  showWatchlistModal.value = true;
}

function closeWatchlistModal() {
  showWatchlistModal.value = false;
}

function handleWatchlistAdded() {
  showWatchlistModal.value = false;
  acquisitionsStore.fetchAll();
}
```

3. Replace the router-link (lines 117-123) with a button:
```html
<!-- Add Item Button -->
<button
  data-testid="add-to-watchlist"
  @click="openWatchlistModal"
  class="block w-full p-3 border-2 border-dashed border-gray-300 rounded-lg text-center text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600"
>
  + Add to Watchlist
</button>
```

4. Add the modal at the bottom of the template (before closing `</div>`):
```html
<!-- Add to Watchlist Modal -->
<AddToWatchlistModal
  v-if="showWatchlistModal"
  @close="closeWatchlistModal"
  @added="handleWatchlistAdded"
/>
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run AcquisitionsView.spec.ts`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue frontend/src/views/__tests__/AcquisitionsView.spec.ts
git commit -m "feat: wire up AddToWatchlistModal in AcquisitionsView"
```

---

## Task 6: Run full test suite and type check

**Files:** None (verification only)

**Step 1: Run all frontend tests**

Run: `cd frontend && npm test -- --run`

Expected: All tests pass (should be ~58+ tests now)

**Step 2: Run TypeScript type check**

Run: `cd frontend && npm run type-check`

Expected: No errors

**Step 3: Run build**

Run: `cd frontend && npm run build`

Expected: Build succeeds

**Step 4: Commit (if any fixes needed)**

Only commit if fixes were required.

---

## Task 7: Manual testing and push

**Step 1: Start dev server**

Run: `cd frontend && npm run dev`

**Step 2: Manual test checklist**

1. Navigate to `/admin/acquisitions`
2. Click "+ Add to Watchlist" button
3. Verify modal opens
4. Fill in Title and select an Author
5. Type a new author name, verify "+ Add" option appears
6. Add a new author inline, verify it's selected
7. Fill optional fields
8. Click "Add to List"
9. Verify book appears in EVALUATING column
10. Verify modal closes

**Step 3: Push to staging**

Run: `git push origin staging`

**Step 4: Monitor CI**

Run: `gh run watch` (latest run)

Expected: All checks pass, deploy succeeds

---

## Summary

| Task | Component | Tests Added |
|------|-----------|-------------|
| 1 | acquisitions store | 1 |
| 2 | references store | 3 |
| 3 | ComboboxWithAdd | 5 |
| 4 | AddToWatchlistModal | 3 |
| 5 | AcquisitionsView | 1 |
| 6-7 | Verification | - |

**Total new tests:** 13
**Estimated implementation time:** 7 tasks × ~15-20 min = 2-3 hours
