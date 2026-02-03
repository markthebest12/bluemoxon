# Changelog

All notable changes to this project will be documented in this file.
This changelog is automatically maintained by [Uplift](https://upliftci.dev/).

## Unreleased

## [v3.1.0](https://github.com/markthebest12/bluemoxon/releases/tag/v3.1.0) - 2026-02-03

- [`5fa98fa`](https://github.com/markthebest12/bluemoxon/commit/5fa98fa4a36f46d70942a23e28c17951ab2cc8ce) feat: add portrait image to ProfileHero with placeholder fallback (#1632) (#1713)
- [`5b8f495`](https://github.com/markthebest12/bluemoxon/commit/5b8f49534386b656a707242fdbeccde0d0a7fd02) feat: add thumbnails and condition badges to connections and timeline (#1634) (#1712)
- [`6f1aa38`](https://github.com/markthebest12/bluemoxon/commit/6f1aa3874534b4cfaf0fbc667c8edeef7b033cd8) feat: add book thumbnails and condition badges to EntityBooks (#1634) (#1711)
- [`2557388`](https://github.com/markthebest12/bluemoxon/commit/25573881af540badf686b1e08f23d6d5f4ce6533) feat: add acquisition history timeline chart to entity profile (#1633) (#1710)
- [`be30e09`](https://github.com/markthebest12/bluemoxon/commit/be30e094ac78bfcf95ae4ac3b9b7710221b9ea92) feat: add condition breakdown stacked bar to CollectionStats (#1633) (#1709)
- [`5b39f43`](https://github.com/markthebest12/bluemoxon/commit/5b39f434ba98933adb06fd0941c75bbd211be615) feat: add NLS historical map tile fallback for entity portraits (#1632) (#1708)
- [`85dece5`](https://github.com/markthebest12/bluemoxon/commit/85dece5670a34b18c4c020d8dd069e1e9195960b) feat: add frontend types, conditionColors utility, and ConditionBadge component (#1707)
- [`e324b52`](https://github.com/markthebest12/bluemoxon/commit/e324b523390ad1b8ef945643c00e695e099578c1) feat: add frontend types, conditionColors utility, and ConditionBadge component (#1706)
- [`ca40e33`](https://github.com/markthebest12/bluemoxon/commit/ca40e333df0ebb49f68facc17f8db1460168b348) feat: Wikidata portrait matching pipeline with confidence scoring (#1632) (#1705)
- [`49fd612`](https://github.com/markthebest12/bluemoxon/commit/49fd612a374f555906f8609e5b3cded0c244007c) feat: add entity image_url schema and admin portrait upload (#1632) (#1704)
- [`cbffb6e`](https://github.com/markthebest12/bluemoxon/commit/cbffb6eb81153c3b05fa7b551e02176ae7975c62) feat: add primary_image_url to ProfileBook schema (#1634) (#1703)
- [`24b9daf`](https://github.com/markthebest12/bluemoxon/commit/24b9dafb3eb829d774d9cc8d2faa59103920cde8) feat: add condition distribution and acquisition timeline to profile stats (#1633) (#1702)
- [`0208ce3`](https://github.com/markthebest12/bluemoxon/commit/0208ce31480425edd5b7f3e5eab0d264948161f2) Merge pull request #1735 from markthebest12/staging
- [`46b506c`](https://github.com/markthebest12/bluemoxon/commit/46b506c7b44a71102a64d699f64c60e132e58576) fix: use Keep a Changelog format for Uplift compatibility (#1734)
- [`8acb0ed`](https://github.com/markthebest12/bluemoxon/commit/8acb0ed47bde0b5f2f1e7b71be96b2b77f63881c) fix: add size limit and error handling to portrait upload endpoint (#1730)
- [`ec490f4`](https://github.com/markthebest12/bluemoxon/commit/ec490f460261be0010571b6327386baa827a28da) fix: handle malformed AI-generated entity cross-link markers (#1716) (#1729)
- [`745e6e6`](https://github.com/markthebest12/bluemoxon/commit/745e6e6904c350fc18abe6d01ada605e2357e3c4) fix: remove owner_id filter from profile reads and log null biographies (#1715, #1717) (#1728)
- [`8108b78`](https://github.com/markthebest12/bluemoxon/commit/8108b786947aa07c4e4e4b93bc84c1a50bae3493) fix: Wikidata portrait scoring and download bugs (#1632) (#1719) (#1720)
- [`fc95760`](https://github.com/markthebest12/bluemoxon/commit/fc957600e2e766a018c93807fa97360d95e85259) fix: use docker-safe version tags for container image builds
- [`281eb9c`](https://github.com/markthebest12/bluemoxon/commit/281eb9ceebd90aa4227a2bb812ff4a319fcd3127) fix: correct alembic migration down_revision chain (#1632)
- [`49fd612`](https://github.com/markthebest12/bluemoxon/commit/49fd612a374f555906f8609e5b3cded0c244007c) feat: add entity image_url schema and admin portrait upload (#1632) (#1704)

## [v3.0.1] - 2026-02-02

Version 3.0.1 is the first semantically versioned release. Prior versions used
date-based tags (`vYYYY.MM.DD-<sha>`). The version number reflects the maturity
of the project at the time of the semver transition — it is not a jump from 0.1.0.

### Added

- Semantic versioning via Uplift
- PR title validation (conventional commits)
- Version display in navigation bar
- Tag-based production deploy triggers (`v*`)
