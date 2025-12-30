import { ref, watch, type Ref } from "vue";

/**
 * Creates a debounced ref that updates after the specified delay.
 * Replaces @vueuse/core's refDebounced to avoid bundle bloat from
 * multiple VueUse versions (Amplify uses 7.x, we'd need 14.x).
 */
export function refDebounced<T>(source: Ref<T>, delay: number): Ref<T> {
  const debounced = ref(source.value) as Ref<T>;
  let timeout: ReturnType<typeof setTimeout> | undefined;

  watch(source, (val) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => {
      debounced.value = val;
    }, delay);
  });

  return debounced;
}
