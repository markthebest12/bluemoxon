# Design: Theming & Print Features (#510, #511)

**Date:** 2025-12-21
**Issues:** #510, #511

---

## Issue #510: Insurance Report Theming

### Problem
InsuranceReportView.vue is the only page not using the Victorian theme. It uses scoped CSS with Georgia serif font and hard-coded colors.

### Solution
Refactor to use Tailwind Victorian theme classes:

| Current | Replace With |
|---------|--------------|
| `font-family: "Georgia", serif` | `font-display` class |
| `#2c5282` (navy) | `bg-victorian-hunter-800` |
| `#1a365d` (dark navy) | `text-victorian-hunter-900` |
| `#f7fafc` (light gray) | `bg-victorian-paper` |
| Custom `.btn-primary` | Global `btn-primary` class |

### Files Modified
- `frontend/src/views/InsuranceReportView.vue`

---

## Issue #511: Print Capability

### Problem
No print functionality on book view and analysis view pages.

### Solution
Add subtle print buttons similar to InsuranceReportView:

1. **BookDetailView.vue**
   - Print button in action area (near Edit/Delete)
   - Small icon-based, muted color
   - Hide interactive elements when printing

2. **AnalysisViewer.vue**
   - Print button in header (near Edit/Regenerate)
   - Small icon button, subtle styling
   - Print rendered markdown, hide editing UI

### Button Styling
- Small gray/muted button (not prominent)
- Printer icon
- `.no-print` class to hide during printing

### Print CSS
- `@media print` rules added to both components
- Hide `.no-print` elements
- Optimize layout for paper

### Files Modified
- `frontend/src/views/BookDetailView.vue`
- `frontend/src/components/books/AnalysisViewer.vue`

---

## Implementation Order
1. Issue #510: Theme InsuranceReportView.vue
2. Issue #511: Add print to BookDetailView.vue
3. Issue #511: Add print to AnalysisViewer.vue
4. Test both features
5. Create PR to staging
