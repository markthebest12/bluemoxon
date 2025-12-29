# Animation System Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add micro-interactions and polish animations across the BlueMoxon frontend for a more refined user experience.

**Architecture:** CSS-first approach using Tailwind v4's `@theme` for design tokens and `@layer components` for reusable animation classes. Vue `<Transition>` components wrap animated elements.

**Tech Stack:** Tailwind CSS v4, Vue 3 Transitions, CSS custom properties

**Issue:** #624

---

## Section 1: Animation Design Tokens

Add to `frontend/src/assets/main.css` within `@theme`:

```css
@theme {
  /* Durations */
  --duration-instant: 75ms;    /* Micro-feedback (button press) */
  --duration-fast: 150ms;      /* Hover states, small transitions */
  --duration-normal: 250ms;    /* Modals, dropdowns, standard UI */
  --duration-slow: 400ms;      /* Page transitions, large reveals */
  --duration-slower: 600ms;    /* Skeleton pulse, ambient motion */

  /* Easings */
  --ease-out-soft: cubic-bezier(0.25, 0.1, 0.25, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

---

## Section 2: Hover States & Interactive Feedback

Add to `@layer components`:

```css
@layer components {
  /* Card hover - subtle lift */
  .card-interactive {
    transition: transform var(--duration-fast) var(--ease-out-soft),
                box-shadow var(--duration-fast) var(--ease-out-soft);
  }
  .card-interactive:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px -4px rgb(0 0 0 / 0.1),
                0 4px 6px -2px rgb(0 0 0 / 0.05);
  }

  /* Button press feedback */
  .btn-press {
    transition: transform var(--duration-instant) var(--ease-out-soft);
  }
  .btn-press:active {
    transform: scale(0.97);
  }

  /* Animated link underline */
  .link-animated {
    position: relative;
  }
  .link-animated::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 1px;
    background: currentColor;
    transform: scaleX(0);
    transform-origin: right;
    transition: transform var(--duration-fast) var(--ease-out-soft);
  }
  .link-animated:hover::after {
    transform: scaleX(1);
    transform-origin: left;
  }
}
```

---

## Section 3: Modal & Dropdown Transitions

Add to `@layer components`:

```css
@layer components {
  /* Modal backdrop fade */
  .modal-backdrop-enter-from,
  .modal-backdrop-leave-to {
    opacity: 0;
  }
  .modal-backdrop-enter-active,
  .modal-backdrop-leave-active {
    transition: opacity var(--duration-normal) var(--ease-out-soft);
  }

  /* Modal content - fade + slide + scale */
  .modal-enter-from {
    opacity: 0;
    transform: translateY(16px) scale(0.98);
  }
  .modal-leave-to {
    opacity: 0;
    transform: translateY(-8px) scale(0.98);
  }
  .modal-enter-active {
    transition: all var(--duration-normal) var(--ease-spring);
  }
  .modal-leave-active {
    transition: all var(--duration-fast) var(--ease-out-soft);
  }

  /* Dropdown menu */
  .dropdown-enter-from,
  .dropdown-leave-to {
    opacity: 0;
    transform: translateY(-4px);
  }
  .dropdown-enter-active,
  .dropdown-leave-active {
    transition: all var(--duration-fast) var(--ease-out-soft);
  }
}
```

---

## Section 4: Loading States

Add to `@layer components`:

```css
@layer components {
  /* Skeleton loading */
  .skeleton {
    background: linear-gradient(
      90deg,
      rgb(0 0 0 / 0.06) 25%,
      rgb(0 0 0 / 0.12) 50%,
      rgb(0 0 0 / 0.06) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-pulse var(--duration-slower) var(--ease-in-out) infinite;
    border-radius: 4px;
  }

  @keyframes skeleton-pulse {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .skeleton-text {
    height: 1em;
    margin-bottom: 0.5em;
  }
  .skeleton-title {
    height: 1.5em;
    width: 60%;
  }
  .skeleton-image {
    aspect-ratio: 4/3;
  }

  /* Progress bar */
  .progress-bar {
    height: 4px;
    background: rgb(0 0 0 / 0.1);
    border-radius: 2px;
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: var(--color-primary);
    transition: width var(--duration-normal) var(--ease-out-soft);
  }

  /* Indeterminate progress */
  .progress-bar-indeterminate .progress-bar-fill {
    width: 30%;
    animation: progress-slide 1.5s var(--ease-in-out) infinite;
  }

  @keyframes progress-slide {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }

  /* Spinner */
  .spinner {
    width: 1.25em;
    height: 1.25em;
    border: 2px solid rgb(0 0 0 / 0.1);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: spin var(--duration-slow) linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
}
```

---

## Section 5: Component Application

### Class Assignment Table

| Component | Classes | Notes |
|-----------|---------|-------|
| Book cards (grid view) | `card-interactive` | Hover lift effect |
| Acquisition row items | `card-interactive` | Subtle hover feedback |
| Primary/secondary buttons | `btn-press` | Press feedback on click |
| Nav links, breadcrumbs | `link-animated` | Underline on hover |
| Modals (ConfirmDialog, etc.) | `modal-*` transition classes | Fade + slide |
| Dropdowns (filters, menus) | `dropdown-*` transition classes | Quick fade + slide |
| Book card skeleton | `skeleton skeleton-image` | During list loading |
| Table row skeleton | `skeleton skeleton-text` | During table loading |
| AI analysis panel | `progress-bar` | During generation |
| Save/delete buttons | `spinner` (inline) | During async operation |

### Vue Transition Pattern

```vue
<!-- Modal wrapper component -->
<Transition
  enter-from-class="modal-enter-from"
  enter-active-class="modal-enter-active"
  leave-to-class="modal-leave-to"
  leave-active-class="modal-leave-active"
>
  <div v-if="isOpen" class="modal-content">
    <slot />
  </div>
</Transition>
```

### Testing Approach

1. **Visual regression** - Playwright screenshots before/after
2. **Reduced motion** - Test with `prefers-reduced-motion: reduce`
3. **Manual QA checklist** - Each animation category tested on real device

---

## Implementation Notes

- All CSS goes in `frontend/src/assets/main.css`
- Apply classes incrementally to components
- Test each category before moving to next
- Commit after each working section
