import {afterEach, describe, expect, it} from "vitest";
import {BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip} from "chart.js";

import {configurePlots, getPlotColors} from "@/logic/plots";

const colorVariables = {
  "--ffun-plot-feed-missing-data": "#010101",
  "--ffun-plot-feed-zero": "#020202",
  "--ffun-plot-feed-value": "#030303",
  "--ffun-plot-token-day": "#040404",
  "--ffun-plot-token-month": "#050505",
  "--ffun-plot-token-lifetime": "#060606",
  "--ffun-plot-axis": "#070707",
  "--ffun-plot-grid": "#080808",
  "--ffun-plot-text": "#090909",
  "--ffun-plot-tooltip-background": "#101010",
  "--ffun-plot-tooltip-border": "#111111"
} as const;

const originalChartDefaults = {
  responsive: ChartJS.defaults.responsive,
  maintainAspectRatio: ChartJS.defaults.maintainAspectRatio,
  animation: ChartJS.defaults.animation
};

function applyColorVariables(): void {
  for (const [property, color] of Object.entries(colorVariables)) {
    document.documentElement.style.setProperty(property, color);
  }
}

afterEach(() => {
  for (const property of Object.keys(colorVariables)) {
    document.documentElement.style.removeProperty(property);
  }
});

describe("configurePlots", () => {
  afterEach(() => {
    ChartJS.unregister(BarElement, CategoryScale, Legend, LinearScale, Tooltip);
    ChartJS.defaults.responsive = originalChartDefaults.responsive;
    ChartJS.defaults.maintainAspectRatio = originalChartDefaults.maintainAspectRatio;
    ChartJS.defaults.animation = originalChartDefaults.animation;
  });

  it("registers bar-chart primitives and configures application-wide defaults", () => {
    applyColorVariables();
    configurePlots();

    expect(ChartJS.registry.getElement("bar")).toBe(BarElement);
    expect(ChartJS.registry.getScale("category")).toBe(CategoryScale);
    expect(ChartJS.registry.getScale("linear")).toBe(LinearScale);
    expect(ChartJS.registry.getPlugin("legend")).toBe(Legend);
    expect(ChartJS.registry.getPlugin("tooltip")).toBe(Tooltip);
    expect(ChartJS.defaults.responsive).toBe(true);
    expect(ChartJS.defaults.maintainAspectRatio).toBe(false);
    expect(ChartJS.defaults.animation).toBe(false);
    expect(ChartJS.defaults.plugins.legend.display).toBe(false);
    expect(ChartJS.defaults.plugins.tooltip).toMatchObject({
      backgroundColor: "#101010",
      borderColor: "#111111",
      borderWidth: 1,
      padding: 8
    });
  });
});

describe("getPlotColors", () => {
  it("resolves the semantic plot palette from root CSS variables", () => {
    applyColorVariables();

    expect(getPlotColors()).toEqual({
      feedEntries: {
        missingData: "#010101",
        zero: "#020202",
        value: "#030303"
      },
      tokenUsage: {
        day: "#040404",
        month: "#050505",
        lifetime: "#060606"
      },
      axis: "#070707",
      grid: "#080808",
      text: "#090909",
      tooltip: {
        background: "#101010",
        border: "#111111"
      }
    });
  });
});
