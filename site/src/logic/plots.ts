import {BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip} from "chart.js";

export function configurePlots(): void {
  ChartJS.register(BarElement, CategoryScale, Legend, LinearScale, Tooltip);

  const colors = getPlotColors();

  ChartJS.defaults.responsive = true;
  ChartJS.defaults.maintainAspectRatio = false;
  ChartJS.defaults.animation = false;
  ChartJS.defaults.plugins.legend.display = false;
  ChartJS.defaults.plugins.tooltip.backgroundColor = colors.tooltip.background;
  ChartJS.defaults.plugins.tooltip.borderColor = colors.tooltip.border;
  ChartJS.defaults.plugins.tooltip.borderWidth = 1;
  ChartJS.defaults.plugins.tooltip.padding = 8;
}

function plotColor(styles: CSSStyleDeclaration, property: string): string {
  return styles.getPropertyValue(property).trim();
}

export function getPlotColors() {
  const styles = getComputedStyle(document.documentElement);

  return {
    feedEntries: {
      missingData: plotColor(styles, "--ffun-plot-feed-missing-data"),
      zero: plotColor(styles, "--ffun-plot-feed-zero"),
      value: plotColor(styles, "--ffun-plot-feed-value")
    },
    tokenUsage: {
      day: plotColor(styles, "--ffun-plot-token-day"),
      month: plotColor(styles, "--ffun-plot-token-month"),
      lifetime: plotColor(styles, "--ffun-plot-token-lifetime")
    },
    axis: plotColor(styles, "--ffun-plot-axis"),
    grid: plotColor(styles, "--ffun-plot-grid"),
    text: plotColor(styles, "--ffun-plot-text"),
    tooltip: {
      background: plotColor(styles, "--ffun-plot-tooltip-background"),
      border: plotColor(styles, "--ffun-plot-tooltip-border")
    }
  } as const;
}

export const barPlotOptionFragments = {
  xAxis: {
    border: {
      display: true,
      width: 1
    },
    grid: {
      display: false
    }
  },
  yAxis: {
    beginAtZero: true,
    border: {
      display: false
    },
    ticks: {
      precision: 0
    }
  }
} as const;
