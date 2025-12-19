# Book Detail View Analysis Buttons Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add generate/regenerate analysis buttons with model selector to BookDetailView, using the async job pattern from AcquisitionsView.

**Architecture:** Add analysis job tracking state and functions to BookDetailView. Use `storeToRefs` for reactive access to `activeAnalysisJobs` Map. Show generate button when no analysis exists, regenerate button when analysis exists, inline status when job is running.

**Tech Stack:** Vue 3 Composition API, Pinia (storeToRefs), TypeScript

---

## Task 1: Add Analysis Job State and Imports

**Files:**
- Modify: `frontend/src/views/BookDetailView.vue:1-35`

**Step 1: Add storeToRefs import**

Find this line:
```typescript
import { onMounted, ref, computed } from "vue";
```

Replace with:
```typescript
import { onMounted, ref, computed } from "vue";
import { storeToRefs } from "pinia";
```

**Step 2: Add activeAnalysisJobs destructure**

Find this line (around line 18):
```typescript
const authStore = useAuthStore();
```

Add after it:
```typescript
// Destructure reactive Map for job tracking
const { activeAnalysisJobs } = storeToRefs(booksStore);
```

**Step 3: Add analysis generation state**

Find this block (around line 33-35):
```typescript
// Analysis state
const analysisVisible = ref(false);
const hasAnalysis = computed(() => booksStore.currentBook?.has_analysis ?? false);
```

Replace with:
```typescript
// Analysis state
const analysisVisible = ref(false);
const hasAnalysis = computed(() => booksStore.currentBook?.has_analysis ?? false);

// Analysis generation state
const startingAnalysis = ref(false);
const selectedModel = ref<"sonnet" | "opus">("sonnet");
const modelOptions = [
  { value: "sonnet", label: "Sonnet 4.5" },
  { value: "opus", label: "Opus 4.5" },
];
```

**Step 4: Verify changes compile**

Run: `npm run --prefix frontend type-check`
Expected: No TypeScript errors

**Step 5: Commit**

```bash
git add frontend/src/views/BookDetailView.vue
git commit -m "feat(book-detail): add analysis job state and imports"
```

---

## Task 2: Add Analysis Job Helper Functions

**Files:**
- Modify: `frontend/src/views/BookDetailView.vue` (after existing functions, around line 200)

**Step 1: Add helper functions**

Find the `openAnalysis` function:
```typescript
function openAnalysis() {
  analysisVisible.value = true;
}
```

Add these functions immediately after it:
```typescript
// Analysis job tracking
function isAnalysisRunning(): boolean {
  if (!booksStore.currentBook) return false;
  return booksStore.hasActiveJob(booksStore.currentBook.id);
}

function getJobStatus() {
  if (!booksStore.currentBook) return null;
  return booksStore.getActiveJob(booksStore.currentBook.id);
}

async function handleGenerateAnalysis() {
  const book = booksStore.currentBook;
  if (!book || isAnalysisRunning() || startingAnalysis.value) return;

  startingAnalysis.value = true;
  try {
    await booksStore.generateAnalysisAsync(book.id, selectedModel.value);
  } catch (e: any) {
    console.error("Failed to start analysis:", e);
    const message = e.response?.data?.detail || e.message || "Failed to start analysis";
    alert(message);
  } finally {
    startingAnalysis.value = false;
  }
}
```

**Step 2: Verify changes compile**

Run: `npm run --prefix frontend type-check`
Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add frontend/src/views/BookDetailView.vue
git commit -m "feat(book-detail): add analysis job helper functions"
```

---

## Task 3: Update Analysis Card Template

**Files:**
- Modify: `frontend/src/views/BookDetailView.vue:574-585`

**Step 1: Replace existing analysis card**

Find this block:
```vue
          <!-- Analysis Button -->
          <div v-if="hasAnalysis" class="card bg-victorian-cream border-victorian-burgundy/20">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-lg font-semibold text-gray-800">Detailed Analysis</h2>
                <p class="text-sm text-gray-600 mt-1">
                  View the full Napoleon-style acquisition analysis for this book.
                </p>
              </div>
              <button @click="openAnalysis" class="btn-primary">View Analysis</button>
            </div>
          </div>
```

Replace with:
```vue
          <!-- Analysis Card -->
          <div class="card bg-victorian-cream border-victorian-burgundy/20">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-lg font-semibold text-gray-800">Detailed Analysis</h2>
                <!-- State: Job running -->
                <div
                  v-if="isAnalysisRunning() || booksStore.currentBook?.analysis_job_status"
                  class="text-sm text-blue-600 mt-1 flex items-center gap-1"
                >
                  <span class="animate-spin">&#8987;</span>
                  <span>
                    {{
                      (getJobStatus()?.status || booksStore.currentBook?.analysis_job_status) === "pending"
                        ? "Queued..."
                        : "Analyzing..."
                    }}
                  </span>
                </div>
                <!-- State: Job failed -->
                <p
                  v-else-if="getJobStatus()?.status === 'failed'"
                  class="text-sm text-red-600 mt-1"
                >
                  Analysis failed. Please try again.
                </p>
                <!-- State: Has analysis -->
                <p v-else-if="hasAnalysis" class="text-sm text-gray-600 mt-1">
                  View the full Napoleon-style acquisition analysis for this book.
                </p>
                <!-- State: No analysis (editor/admin can generate) -->
                <p v-else-if="authStore.isEditor" class="text-sm text-gray-600 mt-1">
                  Generate a Napoleon-style acquisition analysis for this book.
                </p>
                <!-- State: No analysis (viewer - no action available) -->
                <p v-else class="text-sm text-gray-500 mt-1">
                  No analysis available for this book.
                </p>
              </div>

              <!-- Action buttons -->
              <div class="flex items-center gap-2">
                <!-- View Analysis button (all users, when analysis exists) -->
                <button
                  v-if="hasAnalysis && !isAnalysisRunning() && !booksStore.currentBook?.analysis_job_status"
                  @click="openAnalysis"
                  class="btn-primary"
                >
                  View Analysis
                </button>

                <!-- Model selector (editor/admin only, when not running) -->
                <select
                  v-if="authStore.isEditor && !isAnalysisRunning() && !booksStore.currentBook?.analysis_job_status"
                  v-model="selectedModel"
                  class="text-sm border border-gray-300 rounded px-2 py-1.5"
                  :disabled="startingAnalysis"
                >
                  <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>

                <!-- Generate button (editor/admin, no analysis exists) -->
                <button
                  v-if="!hasAnalysis && authStore.isEditor && !isAnalysisRunning() && !booksStore.currentBook?.analysis_job_status"
                  @click="handleGenerateAnalysis"
                  :disabled="startingAnalysis"
                  class="btn-primary flex items-center gap-1 disabled:opacity-50"
                >
                  <span v-if="startingAnalysis" class="animate-spin">&#8987;</span>
                  <span v-else>&#9889;</span>
                  {{ startingAnalysis ? "Starting..." : "Generate Analysis" }}
                </button>

                <!-- Regenerate button (editor/admin, analysis exists) -->
                <button
                  v-if="hasAnalysis && authStore.isEditor && !isAnalysisRunning() && !booksStore.currentBook?.analysis_job_status"
                  @click="handleGenerateAnalysis"
                  :disabled="startingAnalysis"
                  class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 flex items-center gap-1"
                  title="Regenerate analysis with selected model"
                >
                  <span v-if="startingAnalysis" class="animate-spin">&#8987;</span>
                  <span v-else>&#128260;</span>
                  {{ startingAnalysis ? "Starting..." : "Regenerate" }}
                </button>
              </div>
            </div>
          </div>
```

**Step 2: Verify changes compile**

Run: `npm run --prefix frontend type-check`
Expected: No TypeScript errors

**Step 3: Commit**

```bash
git add frontend/src/views/BookDetailView.vue
git commit -m "feat(book-detail): add generate/regenerate analysis buttons with model selector"
```

---

## Task 4: Manual Testing

**Step 1: Start dev server**

Run: `npm run --prefix frontend dev`

**Step 2: Test State A - No analysis, editor view**

1. Navigate to a book without analysis (or remove analysis from a test book)
2. Verify: Shows "Generate a Napoleon-style acquisition analysis..."
3. Verify: Model selector dropdown visible (Sonnet 4.5 / Opus 4.5)
4. Verify: "Generate Analysis" button visible with lightning emoji

**Step 3: Test State B - Job running**

1. Click "Generate Analysis"
2. Verify: Button changes to "Starting..." with spinner
3. Verify: After API returns, shows "Queued..." or "Analyzing..."
4. Verify: Buttons are hidden during job

**Step 4: Test State C - Analysis exists, editor view**

1. Navigate to a book with existing analysis
2. Verify: Shows "View the full Napoleon-style acquisition analysis..."
3. Verify: "View Analysis" button visible
4. Verify: Model selector visible
5. Verify: "Regenerate" button visible with refresh emoji

**Step 5: Test State D - Analysis exists, viewer (non-editor)**

1. Log out and log in as viewer role (or use incognito)
2. Navigate to a book with analysis
3. Verify: "View Analysis" button visible
4. Verify: Model selector NOT visible
5. Verify: Regenerate button NOT visible

**Step 6: Test regeneration**

1. As editor, click "Regenerate" on a book with analysis
2. Verify: Job starts and shows progress
3. Verify: After completion, analysis is updated

**Step 7: Commit verification results**

```bash
git add .
git commit -m "test: verify analysis buttons work in BookDetailView"
```

---

## Task 5: Run Linting and Type Checks

**Step 1: Run linting**

Run: `npm run --prefix frontend lint`
Expected: No errors (warnings OK)

**Step 2: Run type check**

Run: `npm run --prefix frontend type-check`
Expected: No errors

**Step 3: Fix any issues found**

If errors found, fix them before proceeding.

**Step 4: Final commit**

```bash
git add .
git commit -m "chore: fix lint/type issues in BookDetailView"
```

---

## Summary

This plan adds generate/regenerate analysis buttons to BookDetailView with:
- Model selector dropdown (Sonnet 4.5 / Opus 4.5)
- Async job pattern matching AcquisitionsView
- Four UI states: no analysis, job running, has analysis (editor), has analysis (viewer)
- Editor/admin visibility for generate/regenerate buttons
- Inline status updates without page refresh
