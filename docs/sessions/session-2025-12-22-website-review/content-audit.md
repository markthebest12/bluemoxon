# Content Audit: FEATURES.md vs Website

**Date:** 2025-12-22
**Status:** Complete

---

## Summary

Compared `docs/FEATURES.md` against `site/index.html` and `site/features.html` to identify gaps.

### Overall Assessment

The website covers most features but is **missing recently shipped features** and **lacks visual depth** on key differentiators.

---

## Features MISSING from Website

### 1. Author Tier System (HIGH PRIORITY)

**Just shipped in #528** - Darwin scoring issue fix

- TIER_1: +15 points (Darwin, Lyell)
- TIER_2: +10 points (Dickens, Collins)
- TIER_3: +5 points (Ruskin)

**Current website says:** "Author Priority" with vague description
**Should say:** Explain the 3-tier author scoring system with examples

### 2. Publisher/Binder Tier Details (MEDIUM)

Website mentions "Tier 1 bindery" and "Tier 1 publisher" in Strategic Fit but doesn't explain:

- What makes a Tier 1 publisher (Moxon, Pickering)
- What makes a Tier 1 binder (Zaehnsdorf, Rivière, Sangorski & Sutcliffe)
- How tiers affect scoring

### 3. Victorian Era Focus (MEDIUM)

The app now has **Victorian theming** but this isn't highlighted:

- Victorian era scoring bonus (1837-1901)
- Target period for acquisitions
- UI theming reflects the period

### 4. Keyboard Navigation (LOW)

FEATURES.md mentions keyboard shortcuts but website doesn't:

- Shortcuts for common actions
- Form navigation support

### 5. Real-time Updates (LOW)

Not mentioned on website:

- Optimistic UI updates
- Background data synchronization
- Toast notifications for actions

---

## Features UNDERREPRESENTED on Website

### 1. Strategic Fit Scoring (7 criteria)

Website mentions "0-7" but doesn't list the actual checklist:

- [ ] Target author match
- [ ] Tier 1 bindery
- [ ] Tier 1 publisher
- [ ] Victorian era (1837-1901)
- [ ] Single volume
- [ ] 40%+ discount from FMV
- [ ] No duplicates in collection

**Recommendation:** Add visual checklist or infographic

### 2. Napoleon Framework Details

Website calls it "Napoleon Framework" but doesn't explain what that means:

- Why "Napoleon"? (comprehensive, strategic analysis)
- What sections are included in the 500+ line analysis
- Sample analysis excerpt would help

### 3. Analysis Auto-Generation Threshold

Website mentions "$450" trigger but buried in text.
**Recommendation:** Make this prominent - it's a key automation feature

### 4. Order Processing Flow

FEATURES.md has detailed flow (paste confirmation → AI extracts → delivery tracking)
Website is vaguer with "Paste-to-Extract"

---

## Diagrams Present in FEATURES.md (not on website)

1. **eBay Import Flow** (Mermaid flowchart)
   - Frontend → API → Scraper → Claude → Reference Matching → Storage

2. **Analysis Generation Sequence** (Mermaid sequence diagram)
   - User → API → SQS → Worker → Bedrock → DB

3. **Authentication Flow** (Mermaid sequence diagram)
   - User → App → Cognito → MFA → JWT → API

**Recommendation:** Add these to website - they're excellent visual explainers

---

## Website Has BUT Features.md Doesn't Emphasize

- Mobile Friendly (website promotes, docs don't)
- Discount Tracking as separate feature
- The actual Claude model version (website says "Claude 4.5", docs say "Claude Sonnet 4")

---

## Screenshots Needing Refresh

Current screenshots show old UI - need refresh for:

1. **Victorian theming** - new color scheme, UI styling
2. **Author tier display** - showing tier badges on books
3. **Score breakdown** - showing tier contributions in scoring

---

## Action Items

### HIGH PRIORITY

1. Add Author Tier System explanation to features page
2. Update screenshots with Victorian theming
3. Capture score breakdown showing tier bonuses

### MEDIUM PRIORITY

4. Add Strategic Fit checklist visual
2. Explain Publisher/Binder tier system
3. Highlight Victorian era focus

### LOW PRIORITY

7. Add keyboard shortcuts section
2. Document real-time update features
3. Add FEATURES.md diagrams to website

---

## Model/Version Consistency Issue

- FEATURES.md: "Claude Sonnet 4"
- Website features.html: "Claude 4.5"
- Website index.html: "Claude Sonnet 4"

**Should standardize to:** "Claude Sonnet 4" (via AWS Bedrock)
