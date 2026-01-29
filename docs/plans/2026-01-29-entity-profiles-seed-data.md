# Entity Profile Seed Data

Reference profiles for building and testing the Entity Profile feature. Two examples: one sparse (EBB, 3 connections) and one rich (Robert Browning, 11 connections).

---

## Profile 1: Elizabeth Barrett Browning (Sparse)

### Entity Data

| Field | Value |
|-------|-------|
| ID | author:31 (entity_id: 31) |
| Name | Elizabeth Barrett Browning |
| Type | Author |
| Tier | TIER_1 |
| Era | Romantic |
| Born | 1806 |
| Died | 1861 |
| Books in collection | 2 |

### AI Bio Summary (reference text)

> One of the most prominent Victorian poets and a central figure in English literature. Elizabeth Barrett Browning's *Sonnets from the Portuguese* remains among the most celebrated love poetry in the English language. A literary celebrity in her own right before her marriage to Robert Browning, she was considered a serious candidate for Poet Laureate upon Wordsworth's death in 1850.

### Books in Collection

| ID | Title | Year | Publisher | Binder | Edition | Condition | Value (mid) |
|----|-------|------|-----------|--------|---------|-----------|-------------|
| 59 | Aurora Leigh: A Poem | 1877 | James Miller | — | American reprint | Near Fine | $175 |
| 608 | Sonnets from the Portuguese | 1920 | Dean & Son Limited | Riviere & Son | Dean & Son Limited Edition | VG+ | $625 |

### Book Details

**Aurora Leigh: A Poem (book 59)**
- Full dark brown morocco, blind-tooled decorative borders, raised bands, gilt spine
- Peacock marbled endpapers in red/blue/gold
- Decorative title page with red ink and EBB portrait vignette
- Purchased 2025-12-06 from eBay (robinrarebooks, Midtown Scholar Bookstore, Harrisburg PA)
- $142.41 acquisition cost, 22.88% ROI
- 10 images available

**Sonnets from the Portuguese (book 608)**
- Full red morocco by Riviere & Son
- Elaborate gilt borders with floral scrollwork and rosette corners
- Spine with raised bands and geometric gilt tooling
- All edges gilt, gilt dentelles, marbled endpapers
- Purchased 2026-01-09, negotiated from £500 to £350
- $523.68 acquisition cost, 19.35% ROI
- 14 images available

### Direct Connections (3)

| Connection | Type | Strength | Shared Books |
|------------|------|----------|--------------|
| James Miller (publisher:33, TIER_3) | publisher | 2 | Aurora Leigh (59) |
| Dean & Son Limited (publisher:255, TIER_3) | publisher | 2 | Sonnets from the Portuguese (608) |
| Riviere & Son (binder:15, TIER_1) | binder | 2 | Sonnets from the Portuguese (608) |

### Key Connection Narratives (reference text)

**Riviere & Son (binder)**
> "Her *Sonnets from the Portuguese* is bound in full red morocco by Riviere & Son, one of the premier Victorian binderies. Riviere bound works for many of the era's greatest authors, connecting Barrett Browning to a tradition of fine bookmaking that spanned the entire Victorian period."

**James Miller (publisher)**
> "The 1877 American reprint of *Aurora Leigh* was published by James Miller, a New York publisher who brought major Victorian works to American readers."

**Dean & Son Limited (publisher)**
> "Dean & Son produced the 1920 edition of *Sonnets from the Portuguese*, a post-Victorian tribute to Barrett Browning's enduring legacy."

### Collection Stats

| Stat | Value |
|------|-------|
| Total books | 2 |
| Total value (mid) | $800 |
| Total acquisition cost | $666.09 |
| First editions | 0 |
| With provenance | 0 |
| Date range | 1877 - 1920 |
| Conditions | 1 Near Fine, 1 Very Good |

### Ego Network Visualization

```
                    James Miller
                   (publisher, T3)
                        │
                   [Aurora Leigh]
                        │
           Elizabeth Barrett Browning ──── Dean & Son
            (author, T1, center)      (publisher, T3)
                        │           [Sonnets Portuguese]
                   [Sonnets Portuguese]
                        │
                   Riviere & Son
                   (binder, T1)
```

3 nodes in ring + EBB at center = 4 total nodes, 3 edges.

---

## Profile 2: Robert Browning (Rich)

### Entity Data

| Field | Value |
|-------|-------|
| ID | author:227 (entity_id: 227) |
| Name | Robert Browning |
| Type | Author |
| Tier | TIER_1 |
| Era | Romantic |
| Born | 1812 |
| Died | 1889 |
| Books in collection | 4 |

### AI Bio Summary (reference text)

> Among the foremost Victorian poets, Robert Browning pioneered the dramatic monologue form and produced works of extraordinary psychological depth. His marriage to Elizabeth Barrett Browning united two of the era's greatest literary figures. Published primarily by Smith, Elder & Co., the premier literary publisher of the Victorian age, Browning's works connected him to a vast network of the period's most significant authors.

### Books in Collection

| ID | Title | Year | Publisher | Binder | Edition | Condition | Value (mid) |
|----|-------|------|-----------|--------|---------|-----------|-------------|
| 341 | Ring and the Book | 1868 | Smith, Elder & Co. | — | First Edition | Good | $500 |
| 2 | Selections from The Poetical Works | 1893-94 | Smith, Elder & Co. | — | New Edition | Very Good | $175 |
| 63 | The Poetical Works | 1898 | Smith, Elder & Co. | Bayntun | Posthumous collected | Near Fine | $650 |
| 57 | Poetical Works of Elizabeth Barrett Browning | 1904 | Oxford University Press | — | Oxford Complete | Very Good | $95 |

### Book Details

**Ring and the Book (book 341) — FIRST EDITION**
- Cloth binding, 4 volumes complete
- Gift inscription from J.V. Jamieson to Mr. & Mrs. Robertson
- Pictorial bookplate of Roger H. West
- Purchased 2025-11-17, $245.84 (50.83% discount, 73% ROI)
- Smith, Elder & Co. Tier 1 publisher
- 9 images available

**Selections from The Poetical Works (book 2)**
- Riviere fine half morocco, brown morocco spine with 5 raised bands
- Green corners, elaborate marbled boards
- First & Second Series bound together
- Confirmed Riviere & Son binding signature on turn-in
- Purchased 2025-12-01 from eBay, $137.17 (21.62% discount, 59% ROI)
- 2 images available

**The Poetical Works (book 63)**
- Full morocco by Bayntun (authenticated)
- 2 volumes, posthumous collected edition
- Bayntun binder signature on front turn-in
- Charles E. Lauriat Co Boston retailer stamp (Tier 3 provenance)
- Purchased 2025-12-08, $336.67 (48.20% discount, 93.07% ROI)
- 11 images available

**Poetical Works of Elizabeth Barrett Browning (book 57)**
- Quarter cream vellum spine with gilt floral tooling
- Green morocco spine label, blue cloth boards, top edge gilt
- Note: This is EBB's collected works published under Oxford/Henry Frowde
- Purchased 2025-12-05 from eBay, $110.58
- 7 images available

### Direct Connections (11)

**Publisher connections:**

| Connection | Type | Strength | Shared Books |
|------------|------|----------|--------------|
| Smith, Elder & Co. (publisher:167, TIER_1) | publisher | 6 | Ring and Book (341), Selections (2), Poetical Works (63) |
| Oxford University Press (publisher:32, TIER_2) | publisher | 2 | EBB Poetical Works (57) |

**Binder connection:**

| Connection | Type | Strength | Shared Books |
|------------|------|----------|--------------|
| Bayntun (binder:4, TIER_1) | binder | 2 | Poetical Works (63) |

**Shared publisher connections (via Smith, Elder & Co.):**

| Connection | Type | Strength | Via Publisher |
|------------|------|----------|--------------|
| George Meredith (author:354, TIER_1) | shared_publisher | 3 | Smith, Elder & Co. |
| John Ruskin (author:260, TIER_3) | shared_publisher | 3 | Smith, Elder & Co. |
| Anthony Trollope (author:258, TIER_1) | shared_publisher | 3 | Smith, Elder & Co. |
| Leigh Hunt (author:231, TIER_2) | shared_publisher | 3 | Smith, Elder & Co. |
| Elizabeth Gaskell (author:263, TIER_2) | shared_publisher | 3 | Smith, Elder & Co. |
| Bronte Sisters (author:252, TIER_1) | shared_publisher | 3 | Smith, Elder & Co. |
| William Makepeace Thackeray (author:223, TIER_1) | shared_publisher | 3 | Smith, Elder & Co. |
| John Keats (author:245, TIER_1) | shared_publisher | 3 | Smith, Elder & Co. |

### Key Connection Narratives (reference text)

**Smith, Elder & Co. (publisher, strength 6) — KEY**
> "Robert Browning's primary publisher, Smith, Elder & Co. was the preeminent literary house of the Victorian era. Three of his four works in this collection bear their imprint, including the landmark first edition of *The Ring and the Book* (1868). Through Smith Elder, Browning joins a constellation of the period's greatest writers."

**Thackeray (shared publisher, strength 3) — KEY**
> "Both published by Smith, Elder & Co., Browning and Thackeray represented the literary heights of Victorian letters — Browning in verse, Thackeray in prose. Smith Elder's roster reads like a who's who of the era."

**Bronte Sisters (shared publisher, strength 3) — KEY**
> "The Brontes and Browning shared Smith, Elder & Co. as their publisher, placing them at the heart of Victorian literature's golden age. Charlotte Bronte's *Jane Eyre* and Browning's dramatic monologues emerged from the same publishing house."

**Bayntun (binder, strength 2)**
> "The posthumous *Poetical Works* (1898) is bound by Bayntun of Bath, one of England's finest binderies. The Lauriat import stamp connects this volume to Boston's premier rare book trade."

**John Keats (shared publisher, strength 3)**
> "Browning and Keats, published decades apart by Smith, Elder & Co., represent the arc from Romantic to Victorian poetry — the younger generation building on the foundation laid by Keats before his early death."

### Collection Stats

| Stat | Value |
|------|-------|
| Total books | 4 |
| Total value (mid) | $1,420 |
| Total acquisition cost | $830.26 |
| First editions | 1 (Ring and the Book) |
| With provenance | 2 |
| Date range | 1868 - 1904 |
| Conditions | 1 Near Fine, 2 Very Good, 1 Good |
| Publishers | Smith Elder (3), OUP (1) |
| Binders | Bayntun (1) |

### Ego Network Visualization

```
                        Leigh Hunt
                       (author, T2)
                            │
              Keats ────── Smith, Elder & Co. ────── Gaskell
           (author, T1)   (publisher, T1)         (author, T2)
                            │
            Trollope ──────┤├────── Bronte Sisters
           (author, T1)    ││      (author, T1)
                           ││
                    Robert Browning ────── OUP
                   (author, T1, center)  (publisher, T2)
                           │
            Thackeray ─────┤
           (author, T1)    │
                           │
              Meredith ────┤
           (author, T1)    │
                           │
              Ruskin ──────┤────── Bayntun
           (author, T3)          (binder, T1)
```

11 nodes in ring + RB at center = 12 total nodes, 11 edges.

---

## Usage Notes

### For Frontend Development
- Use these profiles as the visual reference for building `EntityProfileView.vue`
- EBB tests the sparse case (3 connections, 2 books, no first editions)
- RB tests the rich case (11 connections, 4 books, 1 first edition, provenance)

### For AI Prompt Testing
- The "reference text" for bios and narratives is what we want Claude Haiku to produce
- Use these as evaluation criteria: does the generated text match the quality and tone?

### For Backend API
- The data shapes here map to what `GET /entity/:type/:id/profile` should return
- EBB entity_id=31, RB entity_id=227

### Key Edge Cases Shown
- EBB: No shared-publisher connections (isolated publishers)
- EBB: Mix of Victorian and post-Victorian editions
- RB: Same publisher for 3/4 books (Smith Elder dominance)
- RB: One book is technically EBB's collected works (authored by wife)
- RB: Both publisher and binder connections
- RB: Provenance data on 2 books
- RB: 8 shared-publisher connections all via Smith Elder
