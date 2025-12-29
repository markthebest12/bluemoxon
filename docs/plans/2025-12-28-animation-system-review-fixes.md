# Animation System Code Review Fixes - Session Log

**Date:** 2025-12-28
**Branch:** `feat/624-animation-system`
**PR:** #628

---

## CRITICAL REMINDERS FOR NEXT SESSION

### 1. ALWAYS Use Superpowers Skills
- **MANDATORY:** Check and use relevant skills before ANY task
- Use `superpowers:verification-before-completion` before claiming done
- Use `superpowers:finishing-a-development-branch` when all tasks complete

### 2. Bash Command Rules - NEVER Use These (Permission Prompts)
```bash
# NEVER - triggers prompts:
# Comment lines before commands
command1 \
  --with-continuation    # Backslash continuations
$(date +%s)              # Command substitution
cmd1 && cmd2             # Chaining with &&
cmd1 || cmd2             # Chaining with ||
--password 'Test1234!'   # ! in quoted strings
```

### 3. Bash Command Rules - ALWAYS Use These
```bash
# ALWAYS - auto-approved:
npm run --prefix frontend type-check
git add file1.vue file2.vue
git commit -m "message"
bmx-api GET /books        # For all API calls
```
- Use separate sequential Bash tool calls instead of &&
- Use `bmx-api` for all BlueMoxon API calls

---

## Current State: TYPE ERRORS - NEEDS FIXING

Type-check fails with unused import errors. Must fix these imports:

```
src/components/AcquireModal.vue - remove: watch, onUnmounted
src/components/AddToWatchlistModal.vue - remove: watch, onUnmounted
src/components/AddTrackingModal.vue - remove: watch, onUnmounted
src/components/books/EvalRunbookModal.vue - remove: onUnmounted
src/components/books/ImageReorderModal.vue - remove: onUnmounted
src/components/books/ImageUploadModal.vue - remove: onUnmounted
src/components/EditWatchlistModal.vue - remove: onUnmounted, watch
src/components/PasteOrderModal.vue - remove: watch, onUnmounted
```

---

## Completed Fixes

| Issue | Fix | Status |
|-------|-----|--------|
| TransitionModal `appear` on wrong Transition | Added `appear` to BOTH backdrop and inner Transition | DONE |
| Plan files committed (1400+ lines) | Removed 3 files from branch | DONE |
| Nested modal scroll lock collision | Centralized in TransitionModal with counter | DONE |
| Hardcoded shadows in card-interactive | Changed to `var(--shadow-md)` | DONE |
| Scroll lock logic in individual modals | Removed from all modals | DONE |

---

## TransitionModal Final Implementation

```vue
<script setup lang="ts">
import { watch, onUnmounted } from "vue";

const props = defineProps<{
  visible: boolean;
}>();

defineEmits<{
  'backdrop-click': [];
}>();

// Track how many modals are open to handle nested modals correctly
let modalCount = 0;

watch(
  () => props.visible,
  (isVisible) => {
    if (isVisible) {
      modalCount++;
      document.body.style.overflow = "hidden";
    } else {
      modalCount--;
      if (modalCount <= 0) {
        modalCount = 0;
        document.body.style.overflow = "";
      }
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (props.visible) {
    modalCount--;
    if (modalCount <= 0) {
      modalCount = 0;
      document.body.style.overflow = "";
    }
  }
});
</script>

<template>
  <Teleport to="body">
    <Transition ... appear>  <!-- appear on BACKDROP -->
      <div v-if="visible" ...>
        <Transition ... appear>  <!-- appear on CONTENT too -->
          <slot />
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
```

---

## Next Steps

1. **Fix unused imports** in 8 files (see list above)
2. **Run verification:**
   ```bash
   npm run --prefix frontend type-check
   npm run --prefix frontend lint
   npm run --prefix frontend test
   npm run --prefix frontend build
   ```
3. **Commit all fixes:**
   ```bash
   git add -A
   git commit -m "fix: Address code review feedback for animation system"
   ```
4. **Push and update PR:**
   ```bash
   git push origin feat/624-animation-system
   ```

---

## Import Fixes Required

### AcquireModal.vue
```typescript
// FROM:
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
// TO:
import { ref, computed, onMounted } from "vue";
```

### AddToWatchlistModal.vue
```typescript
// FROM:
import { ref, computed, onMounted, watch, onUnmounted } from "vue";
// TO:
import { ref, computed, onMounted } from "vue";
```

### AddTrackingModal.vue
```typescript
// FROM:
import { ref, watch, onUnmounted, computed } from "vue";
// TO:
import { ref, computed } from "vue";
```

### EvalRunbookModal.vue
```typescript
// FROM:
import { ref, computed, watch, onUnmounted } from "vue";
// TO:
import { ref, computed, watch } from "vue";
```

### ImageReorderModal.vue
```typescript
// FROM:
import { ref, watch, onUnmounted } from "vue";
// TO:
import { ref, watch } from "vue";
```

### ImageUploadModal.vue
```typescript
// FROM:
import { ref, watch, onUnmounted, computed } from "vue";
// TO:
import { ref, watch, computed } from "vue";
```

### EditWatchlistModal.vue
```typescript
// FROM:
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
// TO:
import { ref, computed, onMounted } from "vue";
```

### PasteOrderModal.vue
```typescript
// FROM:
import { ref, watch, onUnmounted } from "vue";
// TO:
import { ref } from "vue";
```

---

## Files Modified (uncommitted)

- `frontend/src/components/TransitionModal.vue` - centralized scroll lock
- `frontend/src/components/AcquireModal.vue` - removed scroll lock
- `frontend/src/components/AddToWatchlistModal.vue` - removed scroll lock
- `frontend/src/components/AddTrackingModal.vue` - removed scroll lock
- `frontend/src/components/EditWatchlistModal.vue` - removed scroll lock
- `frontend/src/components/PasteOrderModal.vue` - removed scroll lock
- `frontend/src/components/ImportListingModal.vue` - removed scroll lock
- `frontend/src/components/books/EvalRunbookModal.vue` - removed scroll lock
- `frontend/src/components/books/ImageReorderModal.vue` - removed scroll lock
- `frontend/src/components/books/ImageUploadModal.vue` - removed scroll lock
- `frontend/src/assets/main.css` - fixed hardcoded shadow

---

## Resume Command

Continue fixing imports, then run verification and commit.
