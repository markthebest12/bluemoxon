# ADR-002: Click-Outside Timing with requestAnimationFrame

## Status

Accepted

## Date

2026-01-28

## Context

Issue #1412 raised the question of whether `requestAnimationFrame` (rAF) or `setTimeout(fn, 0)` should be used to defer adding a click-outside listener in `useClickOutside.ts`.

### The Problem Being Solved

When a user clicks a button to open a panel, the `useClickOutside` composable is mounted and begins listening for clicks outside the panel. Without deferral, the same click event that opened the panel would immediately trigger the click-outside handler, closing the panel before the user sees it.

### Current Implementation

```typescript
onMounted(() => {
  rafId = requestAnimationFrame(() => {
    document.addEventListener("click", handleClick, true);
  });
});
```

### Alternative Considered

```typescript
onMounted(() => {
  setTimeout(() => {
    document.addEventListener("click", handleClick, true);
  }, 0);
```

## Decision

**Keep `requestAnimationFrame` for deferring the click-outside listener.**

### Technical Comparison

| Aspect | requestAnimationFrame | setTimeout(fn, 0) |
|--------|----------------------|-------------------|
| Timing | Before next paint (~16ms at 60Hz) | Macrotask queue (4-10ms typical) |
| Tab backgrounded | Does NOT fire | Fires normally |
| Semantic intent | "Do this before next render" | "Do this later" |
| Browser optimization | Prioritized for UI work | General-purpose timer |
| Cancellation | `cancelAnimationFrame()` | `clearTimeout()` |

### Why rAF is Correct for This Use Case

1. **Semantic correctness**: We're deferring a UI-related operation (adding a listener that responds to user interaction). rAF is designed for pre-render work.

2. **Guaranteed timing**: rAF fires before the next paint, ensuring the listener is added before the user could possibly click again. `setTimeout(0)` has more variable timing across browsers.

3. **Tab-backgrounding is a non-issue**: The concern that rAF doesn't fire when the tab is backgrounded is irrelevant because:
   - If the user backgrounds the tab immediately after clicking to open, they are by definition not clicking outside
   - When they return to the tab, subsequent interactions work normally
   - The panel remains open (correct behavior) until they actually interact with it

4. **Existing implementation works**: The current code handles the edge case explicitly with cleanup in `onUnmounted`, preventing memory leaks if the component unmounts before rAF fires.

### When setTimeout Would Be Preferred

`setTimeout(fn, 0)` would be better if:

- The deferred work is not UI-related
- The work must happen even when the tab is backgrounded
- Precise timing relative to other macrotasks is important

None of these apply to click-outside detection.

## Consequences

### Positive

- Code uses the semantically correct API for UI-related deferral
- Consistent with browser expectations for animation-frame timing
- No change needed to existing implementation

### Negative

- None identified

### Neutral

- Documentation now exists for future maintainers questioning this choice

## References

- Issue: #1412
- Implementation: `frontend/src/composables/socialcircles/useClickOutside.ts`
- MDN requestAnimationFrame: <https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame>
- MDN setTimeout: <https://developer.mozilla.org/en-US/docs/Web/API/setTimeout>
