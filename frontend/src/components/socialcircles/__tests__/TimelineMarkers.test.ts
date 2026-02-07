import { describe, it, expect } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import TimelineMarkers from "../TimelineMarkers.vue";
import type { HistoricalEvent } from "@/types/socialCircles";
import { VICTORIAN_EVENTS } from "@/constants/socialCircles";

const testEvents: HistoricalEvent[] = [
  { year: 1837, label: "Victoria's Coronation", type: "political" },
  { year: 1851, label: "Great Exhibition", type: "cultural" },
  { year: 1859, label: "Origin of Species", type: "literary" },
  { year: 1901, label: "Victoria Dies", type: "political" },
];

function mountMarkers(props: {
  minYear: number;
  maxYear: number;
  sliderYear?: number;
  events?: HistoricalEvent[];
}) {
  return mount(TimelineMarkers, { props });
}

// =============================================================================
// Position Calculation
// =============================================================================

describe("TimelineMarkers - position calculation", () => {
  it("positions a marker at 0% when year equals minYear", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1800, label: "Start", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.attributes("style")).toContain("left: 0%");
  });

  it("positions a marker at 100% when year equals maxYear", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1900, label: "End", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.attributes("style")).toContain("left: 100%");
  });

  it("positions a marker at 50% when year is midpoint", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Mid", type: "cultural" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.attributes("style")).toContain("left: 50%");
  });

  it("calculates fractional percentages correctly", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1825, label: "Quarter", type: "literary" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.attributes("style")).toContain("left: 25%");
  });
});

// =============================================================================
// Range Filtering
// =============================================================================

describe("TimelineMarkers - range filtering", () => {
  it("shows events within the visible range", () => {
    const wrapper = mountMarkers({
      minYear: 1840,
      maxYear: 1870,
      events: testEvents,
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    expect(markers).toHaveLength(2); // 1851 and 1859
  });

  it("hides events outside the visible range", () => {
    const wrapper = mountMarkers({
      minYear: 1860,
      maxYear: 1890,
      events: testEvents,
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    expect(markers).toHaveLength(0);
  });

  it("includes events at the range boundaries", () => {
    const wrapper = mountMarkers({
      minYear: 1837,
      maxYear: 1901,
      events: testEvents,
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    expect(markers).toHaveLength(4);
  });

  it("shows no markers when events array is empty", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [],
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    expect(markers).toHaveLength(0);
  });
});

// =============================================================================
// Division by Zero (minYear === maxYear)
// =============================================================================

describe("TimelineMarkers - division by zero", () => {
  it("positions marker at 50% when minYear equals maxYear (edge case)", () => {
    const wrapper = mountMarkers({
      minYear: 1850,
      maxYear: 1850,
      events: [{ year: 1850, label: "Same Year", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.attributes("style")).toContain("left: 50%");
  });

  it("does not throw when minYear equals maxYear", () => {
    expect(() =>
      mountMarkers({
        minYear: 1850,
        maxYear: 1850,
        events: [{ year: 1850, label: "Same Year", type: "political" }],
      })
    ).not.toThrow();
  });

  it("returns empty markers when minYear > maxYear (inverted range)", () => {
    const wrapper = mountMarkers({
      minYear: 1900,
      maxYear: 1800,
      events: [{ year: 1850, label: "Inverted Range", type: "political" }],
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    expect(markers).toHaveLength(0);
  });

  it("positions marker at 0% when minYear > maxYear (inverted range guard)", () => {
    const wrapper = mountMarkers({
      minYear: 1900,
      maxYear: 1800,
      events: [],
    });
    expect(wrapper.findAll(".timeline-markers__marker")).toHaveLength(0);
  });
});

// =============================================================================
// Event Type Classes
// =============================================================================

describe("TimelineMarkers - event type classes", () => {
  it("applies political class for political events", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1837, label: "Political Event", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.classes()).toContain("timeline-markers__marker--political");
  });

  it("applies literary class for literary events", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1859, label: "Literary Event", type: "literary" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.classes()).toContain("timeline-markers__marker--literary");
  });

  it("applies cultural class for cultural events", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1851, label: "Cultural Event", type: "cultural" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.classes()).toContain("timeline-markers__marker--cultural");
  });
});

// =============================================================================
// Tooltip Display
// =============================================================================

describe("TimelineMarkers - tooltip rendering", () => {
  it("does not show tooltip by default", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Test Event", type: "political" }],
    });
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(false);
  });

  it("shows tooltip on mouseenter", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Test Event", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    expect(wrapper.find(".timeline-markers__tooltip-label").text()).toBe("Test Event");
    expect(wrapper.find(".timeline-markers__tooltip-type").text()).toBe("political");
  });

  it("hides tooltip on mouseleave", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Test Event", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    await marker.trigger("mouseleave");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(false);
  });

  it("shows tooltip on focus", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Focus Event", type: "cultural" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("focus");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    expect(wrapper.find(".timeline-markers__tooltip-label").text()).toBe("Focus Event");
  });

  it("hides tooltip on blur", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Blur Event", type: "cultural" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("focus");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    await marker.trigger("blur");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(false);
  });

  it("shows tooltip on Enter key (does not toggle off)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Enter Event", type: "literary" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("keydown", { key: "Enter" });
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    await marker.trigger("keydown", { key: "Enter" });
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
  });

  it("shows tooltip on Space key (does not toggle off)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Space Event", type: "literary" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("keydown", { key: " " });
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    await marker.trigger("keydown", { key: " " });
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
  });

  it("dismisses tooltip on Escape key", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Escape Event", type: "literary" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("keydown", { key: "Enter" });
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    await marker.trigger("keydown", { key: "Escape" });
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(false);
  });
});

// =============================================================================
// Tooltip Edge Clamping
// =============================================================================

describe("TimelineMarkers - tooltip edge clamping", () => {
  it("applies left-align class when marker is near left edge (<15%)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1810, label: "Left Edge", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    const tooltip = wrapper.find(".timeline-markers__tooltip");
    expect(tooltip.classes()).toContain("timeline-markers__tooltip--align-left");
  });

  it("applies right-align class when marker is near right edge (>85%)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1890, label: "Right Edge", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    const tooltip = wrapper.find(".timeline-markers__tooltip");
    expect(tooltip.classes()).toContain("timeline-markers__tooltip--align-right");
  });

  it("does not apply edge class when marker is in the middle", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Center", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    const tooltip = wrapper.find(".timeline-markers__tooltip");
    expect(tooltip.classes()).not.toContain("timeline-markers__tooltip--align-left");
    expect(tooltip.classes()).not.toContain("timeline-markers__tooltip--align-right");
  });

  it("does not apply left-align at exactly 15% (boundary)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1815, label: "At 15%", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    const tooltip = wrapper.find(".timeline-markers__tooltip");
    expect(tooltip.classes()).not.toContain("timeline-markers__tooltip--align-left");
  });

  it("does not apply right-align at exactly 85% (boundary)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1885, label: "At 85%", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    const tooltip = wrapper.find(".timeline-markers__tooltip");
    expect(tooltip.classes()).not.toContain("timeline-markers__tooltip--align-right");
  });
});

// =============================================================================
// Accessibility
// =============================================================================

describe("TimelineMarkers - accessibility", () => {
  it("has role=list on the container", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: testEvents,
    });
    const container = wrapper.find(".timeline-markers");
    expect(container.attributes("role")).toBe("list");
  });

  it("has role=listitem on each marker", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1950,
      events: testEvents,
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    markers.forEach((marker) => {
      expect(marker.attributes("role")).toBe("listitem");
    });
  });

  it("has tabindex=0 on each marker for keyboard navigation", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1950,
      events: testEvents,
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    markers.forEach((marker) => {
      expect(marker.attributes("tabindex")).toBe("0");
    });
  });

  it("has descriptive aria-label on each marker", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1950,
      events: [{ year: 1851, label: "Great Exhibition", type: "cultural" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.attributes("aria-label")).toBe("1851: Great Exhibition (cultural)");
  });

  it("tooltip has role=tooltip", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Tooltip Role", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    const tooltip = wrapper.find(".timeline-markers__tooltip");
    expect(tooltip.attributes("role")).toBe("tooltip");
  });

  it("container has aria-label", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [],
    });
    const container = wrapper.find(".timeline-markers");
    expect(container.attributes("aria-label")).toBe("Historical timeline events");
  });

  it("marker has aria-describedby pointing to tooltip when tooltip is visible", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Described Event", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("mouseenter");
    expect(marker.attributes("aria-describedby")).toBe("tooltip-1850-described-event");
    const tooltip = wrapper.find(".timeline-markers__tooltip");
    expect(tooltip.attributes("id")).toBe("tooltip-1850-described-event");
  });

  it("marker does not have aria-describedby when tooltip is hidden", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Hidden Tooltip", type: "cultural" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    expect(marker.attributes("aria-describedby")).toBeUndefined();
  });
});

// =============================================================================
// Touch Tooltip Toggle
// =============================================================================

describe("TimelineMarkers - touch tooltip toggle", () => {
  it("shows tooltip on first click and hides on second click (touch toggle)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [{ year: 1850, label: "Touch Event", type: "political" }],
    });
    const marker = wrapper.find(".timeline-markers__marker");
    await marker.trigger("click");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(true);
    await marker.trigger("click");
    expect(wrapper.find(".timeline-markers__tooltip").exists()).toBe(false);
  });

  it("switches tooltip to different marker on click without dismiss", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [
        { year: 1830, label: "First Event", type: "political" },
        { year: 1870, label: "Second Event", type: "literary" },
      ],
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    await markers[0].trigger("click");
    expect(wrapper.find(".timeline-markers__tooltip-label").text()).toBe("First Event");
    await markers[1].trigger("click");
    expect(wrapper.find(".timeline-markers__tooltip-label").text()).toBe("Second Event");
  });
});

// =============================================================================
// Rapid Hover Switch
// =============================================================================

describe("TimelineMarkers - rapid hover switch", () => {
  it("shows only marker B tooltip when hovering A then immediately B (no mouseleave on A)", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [
        { year: 1830, label: "Marker A", type: "political" },
        { year: 1870, label: "Marker B", type: "literary" },
      ],
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    await markers[0].trigger("mouseenter");
    expect(wrapper.find(".timeline-markers__tooltip-label").text()).toBe("Marker A");

    // Hover marker B without triggering mouseleave on A
    await markers[1].trigger("mouseenter");
    const tooltips = wrapper.findAll(".timeline-markers__tooltip");
    expect(tooltips).toHaveLength(1);
    expect(wrapper.find(".timeline-markers__tooltip-label").text()).toBe("Marker B");
  });
});

// =============================================================================
// Tooltip ID Uniqueness
// =============================================================================

describe("TimelineMarkers - tooltip ID uniqueness", () => {
  it("generates unique tooltip IDs for events with same year and type", async () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [
        { year: 1851, label: "Great Exhibition", type: "cultural" },
        { year: 1851, label: "Crystal Palace Opens", type: "cultural" },
      ],
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    await markers[0].trigger("mouseenter");
    const tooltip1 = wrapper.find(".timeline-markers__tooltip");
    const id1 = tooltip1.attributes("id");

    await markers[0].trigger("mouseleave");
    await markers[1].trigger("mouseenter");
    const tooltip2 = wrapper.find(".timeline-markers__tooltip");
    const id2 = tooltip2.attributes("id");

    expect(id1).not.toBe(id2);
    expect(id1).toBe("tooltip-1851-great-exhibition");
    expect(id2).toBe("tooltip-1851-crystal-palace-opens");
  });
});

// =============================================================================
// Default Events
// =============================================================================

describe("TimelineMarkers - default events", () => {
  it("uses VICTORIAN_EVENTS as default when no events prop is provided", () => {
    const wrapper = mountMarkers({
      minYear: 1700,
      maxYear: 1920,
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    expect(markers).toHaveLength(VICTORIAN_EVENTS.length);
  });

  it("VICTORIAN_EVENTS contains expected historical events", () => {
    expect(VICTORIAN_EVENTS).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ year: 1837, type: "political" }),
        expect.objectContaining({ year: 1851, type: "cultural" }),
        expect.objectContaining({ year: 1859, type: "literary" }),
        expect.objectContaining({ year: 1901, type: "political" }),
      ])
    );
  });

  it("VICTORIAN_EVENTS contains 28 curated events", () => {
    expect(VICTORIAN_EVENTS).toHaveLength(28);
  });

  it("VICTORIAN_EVENTS are sorted by year in ascending order", () => {
    for (let i = 1; i < VICTORIAN_EVENTS.length; i++) {
      expect(VICTORIAN_EVENTS[i].year).toBeGreaterThanOrEqual(VICTORIAN_EVENTS[i - 1].year);
    }
  });
});

// =============================================================================
// Year Label Overlap Prevention
// =============================================================================

describe("TimelineMarkers - year label overlap prevention", () => {
  it("shows all year labels when markers are well-spaced", () => {
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [
        { year: 1810, label: "Event A", type: "political" },
        { year: 1850, label: "Event B", type: "cultural" },
        { year: 1890, label: "Event C", type: "literary" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
  });

  it("hides some year labels when markers cluster together on wide range", () => {
    // Range 1265-1967 = 702 years. Events at 1837,1851,1859 are:
    // 1837: (1837-1265)/702 = 81.48%
    // 1851: (1851-1265)/702 = 83.48%
    // 1859: (1859-1265)/702 = 84.62%
    // Spacing: 1837->1851 is ~2%, 1851->1859 is ~1.14% -- both under 4%
    const wrapper = mountMarkers({
      minYear: 1265,
      maxYear: 1967,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1851, label: "Great Exhibition", type: "cultural" },
        { year: 1859, label: "Origin of Species", type: "literary" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    // All labels exist in DOM (v-show), but only first is visible
    expect(yearLabels).toHaveLength(3);
    expect(yearLabels[0].isVisible()).toBe(true);
    expect(yearLabels[1].isVisible()).toBe(false);
    expect(yearLabels[2].isVisible()).toBe(false);
    expect(yearLabels[0].text()).toBe("1837");
  });

  it("still renders all marker lines even when labels are hidden", () => {
    const wrapper = mountMarkers({
      minYear: 1265,
      maxYear: 1967,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1851, label: "Great Exhibition", type: "cultural" },
        { year: 1859, label: "Origin of Species", type: "literary" },
      ],
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    const lines = wrapper.findAll(".timeline-markers__line");
    expect(markers).toHaveLength(3);
    expect(lines).toHaveLength(3);
  });

  it("reveals hidden year label on hover", async () => {
    const wrapper = mountMarkers({
      minYear: 1265,
      maxYear: 1967,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1851, label: "Great Exhibition", type: "cultural" },
      ],
    });
    let yearLabels = wrapper.findAll(".timeline-markers__year");
    // Initially, only 1837 label is visible (1851 is within 4% so hidden)
    expect(yearLabels).toHaveLength(2);
    expect(yearLabels[0].attributes("style") || "").not.toContain("display: none");
    expect(yearLabels[1].attributes("style") || "").toContain("display: none");

    // Hover the second marker (1851) to reveal its label
    const markers = wrapper.findAll(".timeline-markers__marker");
    await markers[1].trigger("mouseenter");
    yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels[0].attributes("style") || "").not.toContain("display: none");
    expect(yearLabels[1].attributes("style") || "").not.toContain("display: none");
    expect(yearLabels[1].text()).toBe("1851");
  });

  it("reveals hidden year label on focus", async () => {
    const wrapper = mountMarkers({
      minYear: 1265,
      maxYear: 1967,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1851, label: "Great Exhibition", type: "cultural" },
      ],
    });
    let yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(2);
    expect(yearLabels[0].attributes("style") || "").not.toContain("display: none");
    expect(yearLabels[1].attributes("style") || "").toContain("display: none");

    const markers = wrapper.findAll(".timeline-markers__marker");
    await markers[1].trigger("focus");
    yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels[0].attributes("style") || "").not.toContain("display: none");
    expect(yearLabels[1].attributes("style") || "").not.toContain("display: none");
  });

  it("shows all labels on narrow range where spacing exceeds threshold", () => {
    // Range 1837-1901 = 64 years. Events at 1837,1851,1859,1901:
    // 1837: 0%, 1851: 21.87%, 1859: 34.37%, 1901: 100%
    // All spacings exceed 4%
    const wrapper = mountMarkers({
      minYear: 1837,
      maxYear: 1901,
      events: testEvents,
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(4);
  });

  it("shows first label even when all events are clustered", () => {
    // All 3 events within ~1% of each other on a 1000-year range
    const wrapper = mountMarkers({
      minYear: 1000,
      maxYear: 2000,
      events: [
        { year: 1850, label: "Event A", type: "political" },
        { year: 1851, label: "Event B", type: "cultural" },
        { year: 1852, label: "Event C", type: "literary" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
    expect(yearLabels[0].isVisible()).toBe(true);
    expect(yearLabels[1].isVisible()).toBe(false);
    expect(yearLabels[2].isVisible()).toBe(false);
    expect(yearLabels[0].text()).toBe("1850");
  });

  it("hides marker label when too close to slider position", () => {
    // Range 1700-1967 = 267 years. Slider at 1850.
    // Event at 1851: (1851-1700)/267 = 56.55%
    // Slider at 1850: (1850-1700)/267 = 56.18%
    // Gap: 0.37% — well under MIN_LABEL_SPACING (4%)
    const wrapper = mountMarkers({
      minYear: 1700,
      maxYear: 1967,
      sliderYear: 1850,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1851, label: "Great Exhibition", type: "cultural" },
        { year: 1901, label: "Victoria Dies", type: "political" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
    // 1837 visible (far from slider)
    expect(yearLabels[0].isVisible()).toBe(true);
    // 1851 hidden (too close to slider at 1850)
    expect(yearLabels[1].isVisible()).toBe(false);
    // 1901 visible (far from slider)
    expect(yearLabels[2].isVisible()).toBe(true);
  });

  it("shows all markers when sliderYear is not provided", () => {
    const wrapper = mountMarkers({
      minYear: 1837,
      maxYear: 1901,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1870, label: "Education Act", type: "cultural" },
        { year: 1901, label: "Victoria Dies", type: "political" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
    expect(yearLabels[0].isVisible()).toBe(true);
    expect(yearLabels[1].isVisible()).toBe(true);
    expect(yearLabels[2].isVisible()).toBe(true);
  });

  it("updates label visibility reactively when slider moves", async () => {
    const wrapper = mountMarkers({
      minYear: 1837,
      maxYear: 1901,
      sliderYear: 1837,
      events: [{ year: 1870, label: "Education Act", type: "cultural" }],
    });
    let yearLabels = wrapper.findAll(".timeline-markers__year");
    // isVisible() unreliable in JSDOM after reactive prop changes; use style attr
    expect(yearLabels[0].attributes("style") || "").not.toContain("display: none");

    await wrapper.setProps({ sliderYear: 1869 });
    await nextTick();
    yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels[0].attributes("style") || "").toContain("display: none");
  });

  it("slider-hidden marker does not affect marker-to-marker spacing", () => {
    // Range 1700-1900 = 200 years.
    // 1750: 25%, 1755: 27.5%, 1800: 50%
    // Slider at 1759: 29.5%
    // 1750: shown (|25 - 29.5| = 4.5%, not < 4%, first marker)
    // 1755: hidden by slider (|27.5 - 29.5| = 2% < 4%)
    // 1800: should be shown — measures from 1750 (25%), not 1755
    //        gap 50% - 25% = 25% > 4%
    const wrapper = mountMarkers({
      minYear: 1700,
      maxYear: 1900,
      sliderYear: 1759,
      events: [
        { year: 1750, label: "Event A", type: "political" },
        { year: 1755, label: "Event B", type: "cultural" },
        { year: 1800, label: "Event C", type: "literary" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
    // 1750: shown (not hidden by slider, first marker)
    expect(yearLabels[0].attributes("style") || "").not.toContain("display: none");
    // 1755: hidden by slider proximity
    expect(yearLabels[1].attributes("style") || "").toContain("display: none");
    // 1800: shown — spacing measured from 1750 (25%), not hidden 1755
    expect(yearLabels[2].attributes("style") || "").not.toContain("display: none");
  });

  it("preserves marker order by year (sorted left-to-right)", () => {
    // Pass events out of order to verify sorting
    const wrapper = mountMarkers({
      minYear: 1800,
      maxYear: 1900,
      events: [
        { year: 1870, label: "Middle", type: "cultural" },
        { year: 1810, label: "Start", type: "political" },
        { year: 1890, label: "End", type: "literary" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
    expect(yearLabels[0].text()).toBe("1810");
    expect(yearLabels[1].text()).toBe("1870");
    expect(yearLabels[2].text()).toBe("1890");
  });

  it("hides year label on click toggle for hidden-label marker", async () => {
    const wrapper = mountMarkers({
      minYear: 1265,
      maxYear: 1967,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1851, label: "Great Exhibition", type: "cultural" },
      ],
    });
    const markers = wrapper.findAll(".timeline-markers__marker");
    let yearLabels = wrapper.findAll(".timeline-markers__year");

    // Initially, second label is hidden
    expect(yearLabels[1].attributes("style")).toContain("display: none");

    // Click to show
    await markers[1].trigger("click");
    yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels[1].attributes("style")).not.toContain("display: none");

    // Click again to dismiss
    await markers[1].trigger("click");
    yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels[1].attributes("style")).toContain("display: none");
  });
});
