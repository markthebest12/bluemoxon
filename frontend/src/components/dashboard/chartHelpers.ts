import type { AcquisitionDay } from "@/types/dashboard";
import type { Chart, Plugin } from "chart.js";

/**
 * Format tooltip content for acquisition chart data points.
 * Returns an array of strings to display in the tooltip.
 */
export function formatAcquisitionTooltip(day: AcquisitionDay | undefined): string[] {
  if (!day) return [];
  const itemWord = day.count === 1 ? "item" : "items";
  return [
    `Total: $${day.cumulative_value.toLocaleString()}`,
    `Added ${day.label}: ${day.count} ${itemWord} ($${day.value.toLocaleString()})`,
  ];
}

/**
 * Chart.js plugin that shows tooltips when hovering over Y-axis labels.
 * Used for horizontal bar charts (indexAxis: "y") where labels identify entities.
 *
 * Usage:
 * 1. Register the plugin with ChartJS.register(yAxisLabelTooltipPlugin)
 * 2. Add labelTooltips array to chart options: { labelTooltips: ["Tooltip 1", "Tooltip 2", ...] }
 */

// Tooltip DOM element (shared across all charts using this plugin)
let tooltipEl: HTMLDivElement | null = null;
// Track how many charts are using this tooltip (for cleanup)
let activeChartCount = 0;

function getOrCreateTooltip(): HTMLDivElement {
  if (!tooltipEl) {
    tooltipEl = document.createElement("div");
    tooltipEl.id = "y-axis-label-tooltip";
    tooltipEl.style.cssText = `
      position: fixed;
      z-index: 9999;
      padding: 0.5rem 0.75rem;
      font-size: 0.75rem;
      line-height: 1.4;
      color: white;
      background: rgb(17, 24, 39);
      border-radius: 0.375rem;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.15s ease;
      white-space: pre-line;
      max-width: 300px;
    `;
    document.body.appendChild(tooltipEl);
  }
  return tooltipEl;
}

function removeTooltip(): void {
  if (tooltipEl && tooltipEl.parentNode) {
    tooltipEl.parentNode.removeChild(tooltipEl);
    tooltipEl = null;
  }
}

interface LabelTooltipOptions {
  labelTooltips?: string[];
}

export const yAxisLabelTooltipPlugin: Plugin<"bar", LabelTooltipOptions> = {
  id: "yAxisLabelTooltip",

  // Track chart initialization for cleanup
  afterInit() {
    activeChartCount++;
  },

  afterEvent(chart: Chart<"bar">, args) {
    const { event } = args;
    const options = chart.options as LabelTooltipOptions;
    const labelTooltips = options.labelTooltips;

    // Only handle mousemove and mouseout
    if (!labelTooltips || (event.type !== "mousemove" && event.type !== "mouseout")) {
      return;
    }

    const tooltip = getOrCreateTooltip();

    // Hide tooltip on mouseout
    if (event.type === "mouseout") {
      tooltip.style.opacity = "0";
      return;
    }

    // Check if mouse is over a Y-axis label
    const yScale = chart.scales.y;
    if (!yScale || event.x === null || event.y === null) {
      tooltip.style.opacity = "0";
      return;
    }

    // Get the label area bounds (left side of chart)
    const labelAreaRight = yScale.left;
    const labelAreaLeft = chart.chartArea?.left ? 0 : 0; // Labels are to the left of chart area

    // Check if mouse X is in the label area
    if (event.x > labelAreaRight || event.x < labelAreaLeft) {
      tooltip.style.opacity = "0";
      return;
    }

    // Find which label the mouse is over using actual tick positions
    const labels = yScale.ticks;
    let hoveredIndex = -1;

    for (let i = 0; i < labels.length; i++) {
      const labelY = yScale.getPixelForTick(i);
      // Calculate hit box using distance to neighboring ticks (handles non-uniform spacing)
      const prevY = i > 0 ? yScale.getPixelForTick(i - 1) : labelY - yScale.height / labels.length;
      const nextY =
        i < labels.length - 1
          ? yScale.getPixelForTick(i + 1)
          : labelY + yScale.height / labels.length;
      const labelTop = labelY - Math.abs(labelY - prevY) / 2;
      const labelBottom = labelY + Math.abs(nextY - labelY) / 2;

      if (event.y >= labelTop && event.y <= labelBottom) {
        hoveredIndex = i;
        break;
      }
    }

    if (hoveredIndex === -1 || !labelTooltips[hoveredIndex]) {
      tooltip.style.opacity = "0";
      return;
    }

    // Show tooltip with content for this label
    const tooltipContent = labelTooltips[hoveredIndex];
    tooltip.textContent = tooltipContent;
    tooltip.style.opacity = "1";

    // Position tooltip near the mouse but offset to not obscure
    const canvas = chart.canvas;
    const rect = canvas.getBoundingClientRect();
    const mouseX = rect.left + event.x;
    const mouseY = rect.top + event.y;

    // Position to the right of the cursor
    tooltip.style.left = `${mouseX + 15}px`;
    tooltip.style.top = `${mouseY - 10}px`;

    // Ensure tooltip doesn't go off-screen
    const tooltipRect = tooltip.getBoundingClientRect();
    if (tooltipRect.right > window.innerWidth) {
      tooltip.style.left = `${mouseX - tooltipRect.width - 15}px`;
    }
    if (tooltipRect.bottom > window.innerHeight) {
      tooltip.style.top = `${window.innerHeight - tooltipRect.height - 10}px`;
    }
  },

  // Clean up tooltip when chart is destroyed
  beforeDestroy() {
    activeChartCount--;
    // Only remove from DOM when no charts are using it
    if (activeChartCount <= 0) {
      removeTooltip();
      activeChartCount = 0;
    } else if (tooltipEl) {
      // Just hide if other charts still using it
      tooltipEl.style.opacity = "0";
    }
  },
};
