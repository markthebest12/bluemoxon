# Release Notes Page Design

**Date:** 2026-01-23
**Status:** Approved

## Overview

Add a professional release notes page to the marketing site with a timeline-style layout showing version milestones.

## Page Structure

- **File:** `site/releases.html`
- **URL:** `https://www.bluemoxon.com/releases.html`
- **Nav:** Add "Releases" link between "Admin Guide" and "Architecture" on all site pages

### Layout

- Single column, centered (max-width ~800px)
- Dark background matching existing site
- Vertical timeline with version nodes
- Each release is a card connected to the timeline

## Release Content

### v2.1 — January 2026
*"Collection Intelligence"*

- Collection Spotlight — Dashboard showcases top-value books in rotating carousel with premium binding badges
- Interactive Charts — Click any chart segment to filter collection; hover for book counts and sample titles
- Era Classification — Filter by literary period: Pre-Romantic, Romantic, Victorian, Edwardian, Post-1910
- Condition Grades — AB Bookman scale dropdown (Fine → Poor) replaces free-form text
- Dashboard Performance — 40% faster loads via API batching and Redis caching

### v2.0 — December 2025
*"Acquisition Pipeline"*

- eBay Import — Paste listing URL to auto-extract title, author, publisher, price, and images
- Kanban Workflow — Track books through Watchlist → In Transit → On Hand
- Shipment Tracking — Auto-detect carriers (USPS, UPS, FedEx, Royal Mail) with live status updates
- Wayback Archive — One-click preservation of listings to Internet Archive
- Async AI Analysis — Queue Napoleon valuations in background via SQS
- Investment Scoring — Investment Grade (0-100) and Strategic Fit (0-7) calculated at acquisition

### v1.1 — November 2025
*"The Victorian Update"*

- Victorian Dark Mode — Deep burgundy and aged parchment theme inspired by antique bookbinding
- Entity Management — Full CRUD for Authors, Publishers, and Binders with merge/reassignment
- Toast Notifications — User-friendly feedback for errors and confirmations with auto-dismiss
- Reference Library — Tiered scoring for publishers and binderies (Tier 1/2/3 bonuses)

### v1.0 — October 2025
*"Foundation"*

- Collection Catalog — Browse, search, and filter book inventory
- Napoleon AI Valuations — Claude-powered condition assessments and fair market value estimates
- Image Galleries — CDN-delivered photos with lightbox viewing and drag-and-drop reordering
- Book Detail Views — Complete metadata, provenance, and analysis documents
- CSV & PDF Export — Insurance reports and collection summaries

## Visual Design

### Timeline

- Vertical line: 2px, gradient from blue (#3b82f6) to purple (#8b5cf6)
- Version nodes: 12px circles, filled with accent color
- Current version (v2.1): Pulsing glow effect

### Cards

- Semi-transparent background with subtle border
- Version badge: pill-shaped, blue gradient for current, muted for older
- Date: small muted text
- Theme tagline: italic, secondary color
- Feature list: bullet points with blue dots

### Responsive

- Desktop: timeline left, cards right
- Mobile: timeline hidden, cards stack with inline badges

## Site Integration

- Add "Releases" to nav on all pages
- Add footer link: "See what's new →"
- Cross-link to/from features.html

## Meta Tags

- Title: "Release Notes | BlueMoxon"
- Description: "What's new in BlueMoxon - release history and feature updates for the rare book collection management platform."
