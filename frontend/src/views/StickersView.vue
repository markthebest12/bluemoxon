<script setup lang="ts">
import { ref, computed } from "vue";

interface Sticker {
  id: string;
  name: string;
  description: string;
  category: "bookplate" | "seal" | "flourish" | "badge";
  rarity: "common" | "rare" | "legendary";
}

const stickers = ref<Sticker[]>([
  {
    id: "ex-libris-classic",
    name: "Ex Libris Classic",
    description: "The timeless bookplate design, declaring ownership with refined elegance.",
    category: "bookplate",
    rarity: "common",
  },
  {
    id: "wax-seal-burgundy",
    name: "Burgundy Wax Seal",
    description: "An authentic wax seal impression in deep burgundy, bearing the collector's mark.",
    category: "seal",
    rarity: "rare",
  },
  {
    id: "gilded-corner",
    name: "Gilded Corner Flourish",
    description: "Ornate gold corner decoration inspired by medieval manuscripts.",
    category: "flourish",
    rarity: "common",
  },
  {
    id: "first-edition",
    name: "First Edition Badge",
    description: "Mark of distinction for true first printings.",
    category: "badge",
    rarity: "legendary",
  },
  {
    id: "zaehnsdorf-seal",
    name: "Zaehnsdorf Seal",
    description: "Authentication seal for the legendary London bindery.",
    category: "seal",
    rarity: "legendary",
  },
  {
    id: "botanical-frame",
    name: "Botanical Frame",
    description: "Delicate vine and leaf border from Victorian natural history texts.",
    category: "flourish",
    rarity: "rare",
  },
  {
    id: "ex-libris-owl",
    name: "Owl Ex Libris",
    description: "The wise owl guards your literary treasures.",
    category: "bookplate",
    rarity: "rare",
  },
  {
    id: "authenticated-binding",
    name: "Authenticated Binding",
    description: "Official certification of premium binding provenance.",
    category: "badge",
    rarity: "legendary",
  },
  {
    id: "morocco-texture",
    name: "Morocco Leather",
    description: "The distinctive grain of fine goat leather binding.",
    category: "flourish",
    rarity: "common",
  },
  {
    id: "hunter-seal",
    name: "Hunter Green Seal",
    description: "Deep forest seal embodying the collector's spirit.",
    category: "seal",
    rarity: "common",
  },
  {
    id: "riviere-mark",
    name: "Rivière & Son Mark",
    description: "The prestigious stamp of London's finest binders since 1829.",
    category: "badge",
    rarity: "legendary",
  },
  {
    id: "art-nouveau-border",
    name: "Art Nouveau Border",
    description: "Flowing organic lines from the turn of the century.",
    category: "flourish",
    rarity: "rare",
  },
]);

const selectedCategory = ref<string | null>(null);
const hoveredSticker = ref<string | null>(null);

const filteredStickers = computed(() => {
  if (!selectedCategory.value) return stickers.value;
  return stickers.value.filter((s) => s.category === selectedCategory.value);
});

const categories = [
  { id: "bookplate", name: "Bookplates", icon: "📖" },
  { id: "seal", name: "Wax Seals", icon: "⚜️" },
  { id: "flourish", name: "Flourishes", icon: "✦" },
  { id: "badge", name: "Badges", icon: "🏷️" },
];

function getRarityLabel(rarity: string): string {
  return rarity.charAt(0).toUpperCase() + rarity.slice(1);
}
</script>

<template>
  <div class="stickers-page">
    <!-- Decorative Header -->
    <header class="stickers-header">
      <div class="header-ornament header-ornament-left">❧</div>
      <div class="header-content">
        <span class="header-subtitle">The Collector's</span>
        <h1 class="header-title">Sticker Cabinet</h1>
        <p class="header-tagline">Adornments for the Distinguished Bibliophile</p>
      </div>
      <div class="header-ornament header-ornament-right">❧</div>
    </header>

    <!-- Category Filter -->
    <nav class="category-nav">
      <button
        class="category-btn"
        :class="{ active: selectedCategory === null }"
        @click="selectedCategory = null"
      >
        <span class="category-icon">◈</span>
        <span class="category-name">All</span>
      </button>
      <button
        v-for="cat in categories"
        :key="cat.id"
        class="category-btn"
        :class="{ active: selectedCategory === cat.id }"
        @click="selectedCategory = cat.id"
      >
        <span class="category-icon">{{ cat.icon }}</span>
        <span class="category-name">{{ cat.name }}</span>
      </button>
    </nav>

    <!-- Sticker Grid -->
    <div class="sticker-grid">
      <article
        v-for="sticker in filteredStickers"
        :key="sticker.id"
        class="sticker-card"
        :class="[`rarity-${sticker.rarity}`, `category-${sticker.category}`]"
        @mouseenter="hoveredSticker = sticker.id"
        @mouseleave="hoveredSticker = null"
      >
        <!-- Decorative Corner Flourishes -->
        <div class="corner corner-tl"></div>
        <div class="corner corner-tr"></div>
        <div class="corner corner-bl"></div>
        <div class="corner corner-br"></div>

        <!-- Sticker Visual -->
        <div class="sticker-visual">
          <div class="sticker-inner">
            <!-- Bookplate designs -->
            <template v-if="sticker.category === 'bookplate'">
              <div class="bookplate">
                <div class="bookplate-border">
                  <div class="bookplate-content">
                    <span class="bookplate-ex">EX</span>
                    <span class="bookplate-libris">LIBRIS</span>
                    <div class="bookplate-divider"></div>
                    <span class="bookplate-owner">COLLECTOR</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- Wax Seal designs -->
            <template v-else-if="sticker.category === 'seal'">
              <div class="wax-seal" :class="`seal-${sticker.id}`">
                <div class="seal-outer">
                  <div class="seal-inner">
                    <span class="seal-initial">B</span>
                  </div>
                </div>
                <div class="seal-drip seal-drip-1"></div>
                <div class="seal-drip seal-drip-2"></div>
              </div>
            </template>

            <!-- Flourish designs -->
            <template v-else-if="sticker.category === 'flourish'">
              <div class="flourish-design">
                <svg viewBox="0 0 100 100" class="flourish-svg">
                  <path
                    class="flourish-path"
                    d="M10,50 Q25,20 50,50 T90,50"
                    fill="none"
                    stroke-width="2"
                  />
                  <path
                    class="flourish-path"
                    d="M10,50 Q25,80 50,50 T90,50"
                    fill="none"
                    stroke-width="2"
                  />
                  <circle class="flourish-dot" cx="50" cy="50" r="4" />
                </svg>
              </div>
            </template>

            <!-- Badge designs -->
            <template v-else-if="sticker.category === 'badge'">
              <div class="badge-design">
                <div class="badge-ribbon">
                  <div class="ribbon-left"></div>
                  <div class="ribbon-right"></div>
                </div>
                <div class="badge-shield">
                  <span class="badge-text">{{ sticker.name.split(" ")[0].charAt(0) }}</span>
                </div>
              </div>
            </template>
          </div>

          <!-- Shine effect on hover -->
          <div class="sticker-shine" :class="{ active: hoveredSticker === sticker.id }"></div>
        </div>

        <!-- Sticker Info -->
        <div class="sticker-info">
          <h3 class="sticker-name">{{ sticker.name }}</h3>
          <p class="sticker-description">{{ sticker.description }}</p>
          <div class="sticker-meta">
            <span class="rarity-badge" :class="`rarity-${sticker.rarity}`">
              {{ getRarityLabel(sticker.rarity) }}
            </span>
          </div>
        </div>
      </article>
    </div>

    <!-- Footer Flourish -->
    <div class="page-footer">
      <div class="footer-ornament">
        <span>✦</span>
        <span class="footer-line"></span>
        <span>FINIS</span>
        <span class="footer-line"></span>
        <span>✦</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ============================================
   Victorian Sticker Cabinet - Custom Styles
   ============================================ */

/* Google Fonts for extra Victorian flair */
@import url("https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700&family=Cinzel+Decorative:wght@400;700&display=swap");

.stickers-page {
  --gold: #c9a227;
  --gold-light: #d4af37;
  --gold-dark: #a67c00;
  --burgundy: #722f37;
  --burgundy-light: #8b3a42;
  --hunter: #1a3a2f;
  --hunter-light: #254a3d;
  --cream: #f8f5f0;
  --paper: #f0ebe3;
  --ink: #1a1a18;
  --ink-muted: #5c5c58;

  min-height: 100vh;
  padding: 2rem 1rem;
  background:
    radial-gradient(ellipse at top, rgba(201, 162, 39, 0.03) 0%, transparent 50%),
    linear-gradient(180deg, var(--cream) 0%, var(--paper) 100%);
}

/* ============================================
   Header Styles
   ============================================ */

.stickers-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom: 3rem;
  padding: 2rem 1rem;
  position: relative;
}

.header-ornament {
  font-size: 2rem;
  color: var(--gold);
  opacity: 0.7;
  transform: scaleX(-1);
}

.header-ornament-right {
  transform: scaleX(1);
}

.header-content {
  text-align: center;
}

.header-subtitle {
  display: block;
  font-family: "Cinzel", serif;
  font-size: 0.85rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--ink-muted);
  margin-bottom: 0.25rem;
}

.header-title {
  font-family: "Cinzel Decorative", serif;
  font-size: clamp(2rem, 6vw, 3.5rem);
  font-weight: 400;
  color: var(--hunter);
  margin: 0;
  text-shadow:
    1px 1px 0 rgba(201, 162, 39, 0.2),
    2px 2px 4px rgba(0, 0, 0, 0.1);
  letter-spacing: 0.05em;
}

.header-tagline {
  font-family: "Cormorant Garamond", serif;
  font-style: italic;
  font-size: 1.1rem;
  color: var(--ink-muted);
  margin-top: 0.5rem;
}

/* ============================================
   Category Navigation
   ============================================ */

.category-nav {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 3rem;
  padding: 1rem;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(201, 162, 39, 0.05) 50%,
    transparent 100%
  );
}

.category-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: var(--cream);
  border: 1px solid rgba(201, 162, 39, 0.3);
  border-radius: 2px;
  font-family: "Cinzel", serif;
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  color: var(--ink-muted);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.category-btn::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(201, 162, 39, 0.1), transparent);
  transition: left 0.5s ease;
}

.category-btn:hover::before {
  left: 100%;
}

.category-btn:hover {
  border-color: var(--gold);
  color: var(--hunter);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(201, 162, 39, 0.15);
}

.category-btn.active {
  background: var(--hunter);
  border-color: var(--hunter);
  color: var(--gold-light);
  box-shadow:
    0 4px 12px rgba(26, 58, 47, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.category-icon {
  font-size: 1rem;
}

/* ============================================
   Sticker Grid
   ============================================ */

.sticker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* ============================================
   Sticker Card
   ============================================ */

.sticker-card {
  position: relative;
  background: var(--cream);
  border: 1px solid rgba(201, 162, 39, 0.2);
  padding: 1.5rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.sticker-card:hover {
  transform: translateY(-4px);
  box-shadow:
    0 20px 40px rgba(26, 58, 47, 0.15),
    0 0 0 1px rgba(201, 162, 39, 0.3);
}

/* Corner Flourishes */
.corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: var(--gold);
  border-style: solid;
  opacity: 0.4;
  transition: opacity 0.3s ease;
}

.sticker-card:hover .corner {
  opacity: 0.8;
}

.corner-tl {
  top: 8px;
  left: 8px;
  border-width: 2px 0 0 2px;
}
.corner-tr {
  top: 8px;
  right: 8px;
  border-width: 2px 2px 0 0;
}
.corner-bl {
  bottom: 8px;
  left: 8px;
  border-width: 0 0 2px 2px;
}
.corner-br {
  bottom: 8px;
  right: 8px;
  border-width: 0 2px 2px 0;
}

/* ============================================
   Sticker Visual Area
   ============================================ */

.sticker-visual {
  position: relative;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
  background: radial-gradient(ellipse at center, rgba(201, 162, 39, 0.05) 0%, transparent 70%);
  overflow: hidden;
}

.sticker-inner {
  width: 80%;
  height: 80%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: float 6s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

.sticker-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.4),
    transparent
  );
  transform: skewX(-20deg);
  transition: left 0.6s ease;
  pointer-events: none;
}

.sticker-shine.active {
  left: 150%;
}

/* ============================================
   Bookplate Design
   ============================================ */

.bookplate {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bookplate-border {
  width: 90%;
  height: 90%;
  border: 3px double var(--hunter);
  padding: 12px;
  background: var(--paper);
  box-shadow: inset 0 0 20px rgba(26, 58, 47, 0.1);
}

.bookplate-content {
  width: 100%;
  height: 100%;
  border: 1px solid var(--gold-dark);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px;
  background: linear-gradient(180deg, var(--cream) 0%, var(--paper) 100%);
}

.bookplate-ex {
  font-family: "Cinzel Decorative", serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--hunter);
  letter-spacing: 0.3em;
}

.bookplate-libris {
  font-family: "Cinzel", serif;
  font-size: 0.9rem;
  letter-spacing: 0.4em;
  color: var(--hunter);
}

.bookplate-divider {
  width: 60%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--gold),
    transparent
  );
  margin: 8px 0;
}

.bookplate-owner {
  font-family: "Cormorant Garamond", serif;
  font-style: italic;
  font-size: 0.85rem;
  color: var(--ink-muted);
  letter-spacing: 0.2em;
}

/* ============================================
   Wax Seal Design
   ============================================ */

.wax-seal {
  position: relative;
  width: 100px;
  height: 100px;
}

.seal-outer {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--burgundy);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    inset 0 -4px 8px rgba(0, 0, 0, 0.3),
    inset 0 4px 8px rgba(255, 255, 255, 0.1),
    0 4px 12px rgba(114, 47, 55, 0.4);
  position: relative;
}

.seal-outer::before {
  content: "";
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  border: 1px dashed rgba(255, 255, 255, 0.2);
}

.seal-inner {
  width: 60%;
  height: 60%;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--burgundy-light) 0%, var(--burgundy) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
}

.seal-initial {
  font-family: "Cinzel Decorative", serif;
  font-size: 1.8rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.seal-drip {
  position: absolute;
  background: var(--burgundy);
  border-radius: 0 0 50% 50%;
}

.seal-drip-1 {
  width: 15px;
  height: 20px;
  bottom: -12px;
  left: 20px;
  transform: rotate(-10deg);
  box-shadow: 0 2px 4px rgba(114, 47, 55, 0.3);
}

.seal-drip-2 {
  width: 10px;
  height: 14px;
  bottom: -8px;
  right: 25px;
  transform: rotate(15deg);
  box-shadow: 0 2px 4px rgba(114, 47, 55, 0.3);
}

/* Hunter Green Seal Variant */
.seal-hunter-seal .seal-outer {
  background: var(--hunter);
  box-shadow:
    inset 0 -4px 8px rgba(0, 0, 0, 0.3),
    inset 0 4px 8px rgba(255, 255, 255, 0.1),
    0 4px 12px rgba(26, 58, 47, 0.4);
}

.seal-hunter-seal .seal-inner {
  background: linear-gradient(135deg, var(--hunter-light) 0%, var(--hunter) 100%);
}

.seal-hunter-seal .seal-drip {
  background: var(--hunter);
}

/* Zaehnsdorf Gold Seal */
.seal-zaehnsdorf-seal .seal-outer {
  background: linear-gradient(135deg, var(--gold) 0%, var(--gold-dark) 100%);
  box-shadow:
    inset 0 -4px 8px rgba(0, 0, 0, 0.2),
    inset 0 4px 8px rgba(255, 255, 255, 0.3),
    0 4px 12px rgba(201, 162, 39, 0.4);
}

.seal-zaehnsdorf-seal .seal-inner {
  background: linear-gradient(135deg, var(--gold-light) 0%, var(--gold) 100%);
}

.seal-zaehnsdorf-seal .seal-initial {
  color: var(--hunter);
}

.seal-zaehnsdorf-seal .seal-drip {
  background: var(--gold);
}

/* ============================================
   Flourish Design
   ============================================ */

.flourish-design {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.flourish-svg {
  width: 80%;
  height: 80%;
}

.flourish-path {
  stroke: var(--gold);
  stroke-linecap: round;
  stroke-dasharray: 200;
  stroke-dashoffset: 200;
  animation: draw 3s ease-in-out forwards infinite;
}

@keyframes draw {
  0% {
    stroke-dashoffset: 200;
  }
  50% {
    stroke-dashoffset: 0;
  }
  100% {
    stroke-dashoffset: -200;
  }
}

.flourish-dot {
  fill: var(--gold);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform-origin: center;
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
}

/* ============================================
   Badge Design
   ============================================ */

.badge-design {
  position: relative;
  width: 100px;
  height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.badge-ribbon {
  position: absolute;
  bottom: 0;
  width: 100%;
  height: 40px;
  display: flex;
  justify-content: center;
}

.ribbon-left,
.ribbon-right {
  width: 25px;
  height: 40px;
  background: var(--burgundy);
  position: relative;
}

.ribbon-left {
  transform: skewY(10deg);
  transform-origin: top right;
  margin-right: -2px;
}

.ribbon-right {
  transform: skewY(-10deg);
  transform-origin: top left;
  margin-left: -2px;
}

.ribbon-left::after,
.ribbon-right::after {
  content: "";
  position: absolute;
  bottom: 0;
  width: 0;
  height: 0;
  border-style: solid;
}

.ribbon-left::after {
  right: 0;
  border-width: 0 25px 15px 0;
  border-color: transparent var(--cream) transparent transparent;
}

.ribbon-right::after {
  left: 0;
  border-width: 15px 25px 0 0;
  border-color: var(--cream) transparent transparent transparent;
}

.badge-shield {
  width: 80px;
  height: 90px;
  background: linear-gradient(135deg, var(--hunter) 0%, var(--hunter-light) 50%, var(--hunter) 100%);
  border-radius: 0 0 50% 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 4px 12px rgba(26, 58, 47, 0.4),
    inset 0 2px 4px rgba(255, 255, 255, 0.1);
  border: 2px solid var(--gold);
  position: relative;
  z-index: 1;
}

.badge-shield::before {
  content: "";
  position: absolute;
  inset: 4px;
  border: 1px solid rgba(201, 162, 39, 0.3);
  border-radius: 0 0 50% 50%;
}

.badge-text {
  font-family: "Cinzel Decorative", serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--gold-light);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* ============================================
   Sticker Info
   ============================================ */

.sticker-info {
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid rgba(201, 162, 39, 0.2);
}

.sticker-name {
  font-family: "Cinzel", serif;
  font-size: 1rem;
  font-weight: 600;
  color: var(--hunter);
  margin: 0 0 0.5rem;
  letter-spacing: 0.05em;
}

.sticker-description {
  font-family: "Cormorant Garamond", serif;
  font-size: 0.9rem;
  color: var(--ink-muted);
  line-height: 1.5;
  margin: 0 0 1rem;
}

.sticker-meta {
  display: flex;
  justify-content: center;
}

/* Rarity Badges */
.rarity-badge {
  font-family: "Cinzel", serif;
  font-size: 0.65rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 0.35rem 0.75rem;
  border-radius: 1px;
}

.rarity-badge.rarity-common {
  background: var(--paper);
  color: var(--ink-muted);
  border: 1px solid rgba(92, 92, 88, 0.3);
}

.rarity-badge.rarity-rare {
  background: linear-gradient(135deg, var(--burgundy-light) 0%, var(--burgundy) 100%);
  color: white;
  border: 1px solid var(--burgundy-light);
  box-shadow: 0 2px 8px rgba(114, 47, 55, 0.3);
}

.rarity-badge.rarity-legendary {
  background: linear-gradient(135deg, var(--gold-light) 0%, var(--gold) 50%, var(--gold-dark) 100%);
  color: var(--hunter);
  border: 1px solid var(--gold);
  box-shadow:
    0 2px 8px rgba(201, 162, 39, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0%,
  100% {
    box-shadow:
      0 2px 8px rgba(201, 162, 39, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
  50% {
    box-shadow:
      0 2px 16px rgba(201, 162, 39, 0.6),
      inset 0 1px 0 rgba(255, 255, 255, 0.5);
  }
}

/* Card Rarity Accents */
.sticker-card.rarity-legendary {
  border-color: rgba(201, 162, 39, 0.4);
  background: linear-gradient(
    180deg,
    rgba(201, 162, 39, 0.05) 0%,
    var(--cream) 20%,
    var(--cream) 100%
  );
}

.sticker-card.rarity-legendary .corner {
  opacity: 0.8;
  border-color: var(--gold);
}

.sticker-card.rarity-rare {
  border-color: rgba(114, 47, 55, 0.3);
}

.sticker-card.rarity-rare .corner {
  border-color: var(--burgundy);
  opacity: 0.5;
}

/* ============================================
   Footer
   ============================================ */

.page-footer {
  margin-top: 4rem;
  padding: 2rem;
}

.footer-ornament {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  font-family: "Cinzel", serif;
  font-size: 0.8rem;
  letter-spacing: 0.3em;
  color: var(--ink-muted);
}

.footer-line {
  width: 60px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--gold),
    transparent
  );
}

/* ============================================
   Responsive Adjustments
   ============================================ */

@media (max-width: 768px) {
  .stickers-header {
    flex-direction: column;
    gap: 0.5rem;
  }

  .header-ornament {
    display: none;
  }

  .header-title {
    font-size: 2rem;
  }

  .sticker-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1.5rem;
  }

  .category-nav {
    gap: 0.5rem;
  }

  .category-btn {
    padding: 0.5rem 1rem;
    font-size: 0.75rem;
  }

  .category-name {
    display: none;
  }

  .category-icon {
    font-size: 1.2rem;
  }

  .category-btn.active .category-name {
    display: inline;
  }
}

/* Print styles - hide from print */
@media print {
  .stickers-page {
    display: none;
  }
}
</style>
