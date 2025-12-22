# BlueMoxon Books Analysis Processing Plan

**Generated:** 2025-12-20
**Cutoff Timestamp:** 2025-12-20T01:00:00Z (Dec 19, 2025 5:00 PM PST)
**Excluded:** Book #373

## Summary

Total books needing processing: **66 out of 147** (45%)

- **Degraded only:** 26 books (need re-extraction via `/books/{id}/re-extract`)
- **Stale only:** 40 books (need full regeneration via `/books/{id}/analysis`)
- **Both degraded AND stale:** 0 books

## Category 1: Degraded Analysis (26 books)

These books have `extraction_status: "degraded"` and need re-extraction using the new endpoint:

**Endpoint:** `POST /books/{id}/re-extract`

| ID | Title | Updated At |
|----|-------|------------|
| 59 | Aurora Leigh: A Poem | 2025-12-20T22:28:54.734699Z |
| 21 | Coridons Song and Other Verses | 2025-12-20T22:28:36.755695Z |
| 401 | Cranford | 2025-12-20T22:30:10.706173Z |
| 56 | Dante Purgatory (Shadwell/Pater) | 2025-12-20T22:28:50.040936Z |
| 22 | Days with Sir Roger de Coverley | 2025-12-20T22:28:19.323053Z |
| 395 | Encyclopedia Britannica 9th Edition | 2025-12-20T22:30:00.229193Z |
| 60 | Lays of the Scottish Cavaliers and Other Poems | 2025-12-20T22:28:59.375024Z |
| 512 | Memoirs Life of Sir Walter Scott | 2025-12-20T22:27:45.874654Z |
| 399 | Mr Romford's Hounds | 2025-12-20T22:30:13.775874Z |
| 389 | Nature Near London (Bayntun-Riviere) | 2025-12-20T22:29:47.823690Z |
| 62 | Poems of Shelley | 2025-12-20T22:29:41.263630Z |
| 57 | Poetical Works of Elizabeth Barrett Browning | 2025-12-20T22:29:26.854035Z |
| 390 | Practical Lessons on Hunting and Sporting | 2025-12-20T22:29:55.040870Z |
| 2 | Selections from The Poetical Works of Robert Browning | 2025-12-20T22:28:07.812502Z |
| 393 | The Bab Ballads | 2025-12-20T22:30:56.232703Z |
| 24 | The Complete Angler | 2025-12-20T22:28:40.874501Z |
| 4 | The Ethics of the Dust | 2025-12-20T22:28:27.147427Z |
| 391 | The Last Chronicle of Barset | 2025-12-20T22:30:04.919823Z |
| 67 | The Life and Letters of Charles Darwin | 2025-12-20T22:29:36.877964Z |
| 509 | The Life of Oliver Goldsmith, M.B. | 2025-12-20T22:27:37.840866Z |
| 47 | The Poetical Works | 2025-12-20T22:28:44.801490Z |
| 63 | The Poetical Works of Robert Browning | 2025-12-20T22:29:19.483294Z |
| 64 | The Queen of the Air | 2025-12-20T22:29:21.759490Z |
| 66 | The Water-Babies: A Fairy Tale for a Land-Baby | 2025-12-20T22:29:31.295448Z |
| 374 | Tom Brown's School-Days Sangorski | 2025-12-20T22:30:49.418865Z |
| 25 | Travels in the Interior Districts of Africa | 2025-12-20T22:28:32.212180Z |

## Category 2: Stale Analysis (40 books)

These books have `has_analysis: true` but were updated before the cutoff and need full regeneration:

**Endpoint:** `POST /books/{id}/analysis`

| ID | Title | Updated At |
|----|-------|------------|
| 343 | American Gazetteer | 2025-12-13T16:59:26.909424Z |
| 396 | Ariadne Florentina | 2025-12-13T16:59:27.315402Z |
| 489 | A Short History of the English People | 2025-12-18T23:28:42.419717Z |
| 350 | Blessington Literary Life | 2025-12-13T16:59:43.758065Z |
| 336 | Byron Complete Poetical Works | 2025-12-13T16:59:44.590147Z |
| 372 | Byron Vol VIII Beppo-Maz | 2025-12-13T16:59:45.047818Z |
| 383 | Christmas Books (extra copy) | 2025-12-13T16:59:52.483087Z |
| 378 | Court and Times of James I | 2025-12-13T16:59:59.794789Z |
| 68 | Felix Holt, the Radical | 2025-12-14T03:59:51.932299Z |
| 351 | Fielding Select Works | 2025-12-04T16:32:07.284081Z |
| 384 | History of Pendennis (extra copy) | 2025-11-29T19:43:42.076845Z |
| 400 | In Memoriam | 2025-12-04T16:32:07.497591Z |
| 385 | John Masefield Collected Poems | 2025-12-01T16:14:38.566989Z |
| 352 | Kingsley Life/Letters | 2025-12-04T16:32:05.290093Z |
| 403 | Life of John Sterling | 2025-12-11T05:04:07.447575Z |
| 392 | Master Humphrey's Clock Vol I | 2025-12-11T05:04:15.940184Z |
| 405 | Memorials of Early Genius | 2025-12-09T00:35:15.397023Z |
| 339 | Messages & Papers of the Presidents | 2025-11-29T19:43:42.076845Z |
| 27 | Paradise Lost (Dore Illustrated Folio) | 2025-12-11T22:28:40.979720Z |
| 402 | Poetical Works Goldsmith Collins Warton | 2025-12-04T16:32:07.929131Z |
| 397 | Prose Idylls New and Old | 2025-12-03T00:09:00.022891Z |
| 367 | Roundabout Papers (2nd extra copy) | 2025-12-04T16:31:45.631885Z |
| 382 | Roundabout Papers (extra copy) | 2025-12-04T16:32:04.383256Z |
| 398 | Selected Poems of Thomas Hardy | 2025-12-16T01:13:33.743220Z |
| 347 | St Patrick's Eve | 2025-12-02T02:19:27.230813Z |
| 346 | Table-Talk | 2025-12-02T02:19:26.264157Z |
| 335 | Tennyson Complete Poetical Works (Moxon) | 2025-12-04T16:31:44.132437Z |
| 380 | The Four Georges (extra copy) | 2025-12-04T16:32:04.160297Z |
| 3 | The French Revolution | 2025-12-13T16:33:43.544975Z |
| 387 | The Hound of Heaven | 2025-12-02T05:18:27.899982Z |
| 379 | The Life and Works of Charlotte Bronte and Her Sisters | 2025-12-06T05:06:31.297332Z |
| 394 | The Mystery of Edwin Drood | 2025-12-11T05:59:31.766415Z |
| 345 | The Popular Educator | 2025-12-02T02:19:25.503895Z |
| 41 | The Story of the Greatest Nations and The World's Famous Events | 2025-12-09T18:59:04.964839Z |
| 381 | The Virginians (extra copy) | 2025-12-04T16:31:46.918800Z |
| 51 | The Works of William Shakespeare | 2025-12-04T20:27:40.714017Z |
| 348 | Thiers French Revolution | 2025-12-04T16:32:06.160830Z |
| 388 | Vanity Fair Vol II (extra copy) | 2025-12-04T16:31:46.076347Z |
| 356 | Westward Ho! Kingsley | 2025-12-04T16:31:42.160867Z |
| 337 | Works of William Makepeace Thackeray | 2025-11-29T19:43:42.076845Z |

## Processing Strategy

### For Degraded Books (26 books):
```bash
# Use re-extract endpoint
for book_id in 59 21 401 56 22 395 60 512 399 389 62 57 390 2 393 24 4 391 67 509 47 63 64 66 374 25; do
  bmx-api --prod POST /books/$book_id/re-extract
done
```

### For Stale Books (40 books):
```bash
# Use full analysis regeneration endpoint
for book_id in 343 396 489 350 336 372 383 378 68 351 384 400 385 352 403 392 405 339 27 402 397 367 382 398 347 346 335 380 3 387 379 394 345 41 381 51 348 388 356 337; do
  bmx-api --prod POST /books/$book_id/analysis
done
```

## Notes

- Book #373 was explicitly excluded from this analysis per requirements
- All timestamps are in UTC
- Cutoff time: 2025-12-20T01:00:00Z corresponds to Dec 19, 2025 5:00 PM PST
- 0 books were both degraded AND stale (no overlap between categories)
- Full details available in: `.tmp/books_to_process.json`
