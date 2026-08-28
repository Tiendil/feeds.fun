<template>
  <div class="w-full mb-1">
    <div class="h-24">
      <ChartBar
        :data="chartData"
        :options="chartOptions" />
    </div>

    <div class="mt-1 text-xs text-gray-500">{{ label }}</div>
  </div>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import type {ChartData, ChartOptions, TooltipItem} from "chart.js";

  import * as e from "@/logic/enums";
  import {barPlotOptionFragments, getPlotColors} from "@/logic/plots";

  const plotColors = getPlotColors();

  const properties = defineProps<{
    entriesLoadedDetails: number[];
  }>();

  type ChartSlot = {
    value: number;
    padded: boolean;
  };

  const windowSize = e.windowSizes.get(e.TimeGranularity.Day)!;

  const chartSlots = computed<ChartSlot[]>(() => {
    const details = properties.entriesLoadedDetails.slice(-windowSize);
    const missingDays = windowSize - details.length;

    const paddedSlots = Array.from({length: missingDays}, () => {
      return {value: 0, padded: true};
    });

    const loadedSlots = details.map((value) => {
      return {value, padded: false};
    });

    return [...paddedSlots, ...loadedSlots];
  });

  const zeroBarHeight = computed(() => {
    const maxValue = Math.max(...chartSlots.value.map((slot) => slot.value));

    return Math.max(maxValue * 0.04, 0.15);
  });

  const barValues = computed(() => {
    return chartSlots.value.map((slot) => {
      if (slot.value > 0) {
        return slot.value;
      }

      return zeroBarHeight.value;
    });
  });

  const barColors = computed(() => {
    return chartSlots.value.map((slot) => {
      if (slot.padded) {
        return plotColors.feedEntries.missingData;
      }

      if (slot.value === 0) {
        return plotColors.feedEntries.zero;
      }

      return plotColors.feedEntries.value;
    });
  });

  const suggestedMax = computed(() => {
    return Math.max(1, ...chartSlots.value.map((slot) => slot.value));
  });

  function dateForEntry(index: number, entriesCount: number): Date {
    const date = new Date();

    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() - (entriesCount - index - 1));

    return date;
  }

  function formattedDate(date: Date): string {
    return [date.getDate(), date.getMonth() + 1, date.getFullYear()]
      .map((value) => value.toString().padStart(2, "0"))
      .join("-");
  }

  function entriesLabel(count: number, date: Date): string {
    const entriesNoun = count === 1 ? "entry" : "entries";

    return `${count} news ${entriesNoun} loaded on ${formattedDate(date)}`;
  }

  function tooltipLabel(slot: ChartSlot, date: Date): string {
    if (slot.padded) {
      return `No data for ${formattedDate(date)}`;
    }

    return entriesLabel(slot.value, date);
  }

  const dates = computed(() => {
    return chartSlots.value.map((_slot, index) => {
      return dateForEntry(index, chartSlots.value.length);
    });
  });

  const labels = computed(() => {
    return dates.value.map(() => "");
  });

  const label = computed(() => {
    return `Daily news entries loaded over the last ${windowSize} days`;
  });

  const chartData = computed<ChartData<"bar", number[], string>>(() => {
    return {
      labels: labels.value,
      datasets: [
        {
          data: barValues.value,
          backgroundColor: barColors.value,
          hoverBackgroundColor: barColors.value,
          borderRadius: 2,
          borderSkipped: false,
          barPercentage: 0.55,
          categoryPercentage: 0.75
        }
      ]
    };
  });

  const chartOptions = computed<ChartOptions<"bar">>(() => {
    return {
      layout: {
        padding: {
          bottom: 0,
          right: 8
        }
      },
      scales: {
        x: {
          ...barPlotOptionFragments.xAxis,
          offset: true,
          border: {
            ...barPlotOptionFragments.xAxis.border,
            color: plotColors.axis
          },
          ticks: {
            display: false,
            color: plotColors.text,
            font: {
              size: 9
            },
            maxRotation: 0,
            padding: 0,
            autoSkip: false
          }
        },
        y: {
          ...barPlotOptionFragments.yAxis,
          suggestedMax: suggestedMax.value,
          grid: {
            display: false
          },
          ticks: {
            ...barPlotOptionFragments.yAxis.ticks,
            display: false
          }
        }
      },
      plugins: {
        tooltip: {
          displayColors: false,
          callbacks: {
            title: () => "",
            label: (context: TooltipItem<"bar">) => {
              const slot = chartSlots.value[context.dataIndex];

              return tooltipLabel(slot, dates.value[context.dataIndex]);
            }
          }
        }
      }
    };
  });
</script>
