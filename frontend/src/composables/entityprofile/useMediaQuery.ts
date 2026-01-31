import { onMounted, onUnmounted, ref } from "vue";

export function useMediaQuery(query: string) {
  const matches = ref(false);
  let mql: MediaQueryList | null = null;

  function update() {
    matches.value = mql?.matches ?? false;
  }

  onMounted(() => {
    mql = window.matchMedia(query);
    mql.addEventListener("change", update);
    update();
  });

  onUnmounted(() => {
    mql?.removeEventListener("change", update);
  });

  return matches;
}
