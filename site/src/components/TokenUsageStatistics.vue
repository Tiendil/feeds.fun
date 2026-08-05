<template>
  <div>
    <div class="flex flex-wrap items-end gap-x-6 gap-y-3 mb-3">
      <fieldset>
        <legend class="text-sm font-semibold mb-1">Granularity</legend>

        <div class="flex gap-3">
          <label
            v-for="[granularity, option] of e.TimeGranularityProperties"
            :key="granularity"
            class="cursor-pointer">
            <input
              v-model="selectedGranularity"
              type="radio"
              name="token-usage-granularity"
              :value="granularity" />
            {{ option.text }}
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend class="text-sm font-semibold mb-1">Token types</legend>

        <div class="flex flex-wrap gap-3">
          <label
            v-for="[kind, resource] of tokenUsageResources"
            :key="kind"
            class="cursor-pointer">
            <input
              v-model="visibleKinds[kind]"
              class="ffun-checkbox"
              type="checkbox"
              :data-resource-kind="kind" />
            <span
              class="inline-block w-3 h-3 rounded-sm mx-1"
              :style="{backgroundColor: colorForResource(resource)}"></span>
            {{ resource.text }}
          </label>
        </div>
      </fieldset>

      <button
        type="button"
        class="ffun-form-button short"
        :aria-pressed="showAllTime"
        @click="showAllTime = !showAllTime">
        {{ historyButtonLabel }}
      </button>
    </div>

    <p
      v-if="loading"
      aria-live="polite">
      Loading...
    </p>

    <div
      v-else-if="loadError"
      class="ffun-info-bad"
      role="alert">
      <p>Unable to load token usage history. Please try again.</p>
      <button
        type="button"
        class="ffun-form-button short mt-2"
        @click="retryLoading">
        Retry
      </button>
    </div>

    <p v-else-if="visibleTokenUsageResources.length === 0">Select at least one token type to display.</p>

    <template v-else-if="statistics !== null">
      <div class="overflow-x-auto border border-gray-200 rounded-lg">
        <div
          class="h-64 p-2"
          :style="{minWidth: chartMinWidth}">
          <ChartBar
            role="img"
            :aria-label="rangeLabel"
            :data="chartData"
            :options="chartOptions" />
        </div>
      </div>

      <p class="mt-1 text-xs text-gray-500">{{ rangeLabel }}</p>
    </template>
  </div>
</template>

<script lang="ts" setup>
  import {computed, reactive, ref, shallowRef, watch} from "vue";
  import type {ChartData, ChartOptions, TooltipItem} from "chart.js";

  import * as api from "@/logic/api";
  import * as e from "@/logic/enums";
  import {barPlotOptionFragments, getPlotColors} from "@/logic/plots";
  import {
    assertTokenUsageStatistics,
    periodStart,
    shiftDate,
    tokenUsageResourceKinds,
    tokenUsageSlots,
    type TokenUsageStatisticsData,
    type TokenUsageTimeGranularity,
    type TokenUsageResourceKind
  } from "@/logic/resourceStatistics";

  const plotColors = getPlotColors();

  const tokenUsageResources = tokenUsageResourceKinds.map(
    (kind) => [kind, e.ResourceKindProperties.get(kind)!] as const
  );

  const selectedGranularity = ref<TokenUsageTimeGranularity>(e.TimeGranularity.Day);
  const showAllTime = ref(false);
  const visibleKinds = reactive<Record<TokenUsageResourceKind, boolean>>({
    [e.ResourceKind.DayTokenUsage]: true,
    [e.ResourceKind.MonthTokenUsage]: true,
    [e.ResourceKind.LifetimeTokenUsage]: true
  });
  const statistics = shallowRef<TokenUsageStatisticsData | null>(null);
  const loading = ref(false);
  const loadError = ref(false);
  const statisticsCache = new Map<TokenUsageTimeGranularity, TokenUsageStatisticsData>();
  let activeRequest = 0;

  const visibleTokenUsageResources = computed(() => tokenUsageResources.filter(([kind]) => visibleKinds[kind]));

  const dateRange = computed(() => {
    const granularity = selectedGranularity.value;
    const lastDate = periodStart(new Date(), granularity);
    const windowSize = e.windowSizes.get(granularity)!;
    const recentFirstDate = shiftDate(lastDate, 1 - windowSize, granularity);
    const loadedStatistics = statistics.value;

    if (!showAllTime.value || loadedStatistics === null) {
      return {firstDate: recentFirstDate, lastDate};
    }

    const historyFirstTimestamp = Math.min(
      ...tokenUsageResourceKinds.map((kind) =>
        periodStart(loadedStatistics.statistics[kind].firstDate, granularity).getTime()
      )
    );

    return {
      firstDate: new Date(Math.min(recentFirstDate.getTime(), historyFirstTimestamp)),
      lastDate
    };
  });

  const slots = computed(() => {
    if (statistics.value === null) {
      return [];
    }

    return tokenUsageSlots({
      statistics: statistics.value,
      granularity: selectedGranularity.value,
      firstDate: dateRange.value.firstDate,
      lastDate: dateRange.value.lastDate
    });
  });

  function formatPeriod(date: Date, granularity: TokenUsageTimeGranularity): string {
    const options: Intl.DateTimeFormatOptions = {
      year: "numeric",
      timeZone: "UTC"
    };

    if (granularity !== e.TimeGranularity.Year) {
      options.month = "short";
    }

    if (granularity === e.TimeGranularity.Day) {
      options.day = "numeric";
    }

    return new Intl.DateTimeFormat("en-US", options).format(date);
  }

  function formatAmount(value: number): string {
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: Number.isInteger(value) ? 0 : 20
    }).format(value);
  }

  function colorForResource(resource: e.ResourceKindProperty): string {
    if (resource.plotColor === undefined || !(resource.plotColor in plotColors.tokenUsage)) {
      throw new Error("Resource kind does not define a plot color");
    }

    return plotColors.tokenUsage[resource.plotColor as keyof typeof plotColors.tokenUsage];
  }

  const chartData = computed<ChartData<"bar", number[], string>>(() => ({
    labels: slots.value.map((slot) => formatPeriod(slot.date, selectedGranularity.value)),
    datasets: visibleTokenUsageResources.value.map(([kind, resource]) => {
      const color = colorForResource(resource);

      return {
        label: resource.text,
        data: slots.value.map((slot) => slot.values[kind]),
        backgroundColor: color,
        hoverBackgroundColor: color,
        borderRadius: 2,
        borderSkipped: false,
        barPercentage: 0.65,
        categoryPercentage: 0.8
      };
    })
  }));

  const chartOptions = computed<ChartOptions<"bar">>(() => ({
    interaction: {
      mode: "index",
      intersect: false
    },
    scales: {
      x: {
        ...barPlotOptionFragments.xAxis,
        stacked: true,
        border: {
          ...barPlotOptionFragments.xAxis.border,
          color: plotColors.axis
        },
        ticks: {
          color: plotColors.text,
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: selectedGranularity.value === e.TimeGranularity.Day ? 10 : 12
        }
      },
      y: {
        ...barPlotOptionFragments.yAxis,
        stacked: true,
        grid: {
          color: plotColors.grid
        }
      }
    },
    plugins: {
      tooltip: {
        mode: "index",
        intersect: false,
        displayColors: true,
        callbacks: {
          label: (context: TooltipItem<"bar">) => {
            return `${context.dataset.label}: ${formatAmount(Number(context.raw))}`;
          }
        }
      }
    }
  }));

  const chartMinWidth = computed(() =>
    showAllTime.value ? `max(100%, ${Math.max(640, slots.value.length * 14)}px)` : "100%"
  );

  const rangeLabel = computed(() => {
    if (slots.value.length === 0) {
      return "Token usage history";
    }

    const firstDate = formatPeriod(slots.value[0].date, selectedGranularity.value);
    const lastDate = formatPeriod(slots.value[slots.value.length - 1].date, selectedGranularity.value);
    const granularityText = e.TimeGranularityProperties.get(selectedGranularity.value)!.text;
    const granularityLabel = granularityText.charAt(0).toUpperCase() + granularityText.slice(1);

    return `${granularityLabel} token usage from ${firstDate} to ${lastDate}`;
  });

  const historyButtonLabel = computed(() => {
    if (!showAllTime.value) {
      return "For the all time";
    }

    return `For the last ${e.windowSizes.get(selectedGranularity.value)!} ${selectedGranularity.value}s`;
  });

  async function loadStatistics(granularity: TokenUsageTimeGranularity): Promise<void> {
    const request = ++activeRequest;
    const cachedStatistics = statisticsCache.get(granularity);

    if (cachedStatistics !== undefined) {
      statistics.value = cachedStatistics;
      loading.value = false;
      loadError.value = false;
      return;
    }

    statistics.value = null;
    loading.value = true;
    loadError.value = false;

    try {
      const loadedStatistics = await api.getResourceStatistics({
        kinds: [...tokenUsageResourceKinds],
        interval: e.TimeGranularityProperties.get(granularity)!.resourceApiId
      });
      assertTokenUsageStatistics(loadedStatistics);

      statisticsCache.set(granularity, loadedStatistics);

      if (request === activeRequest && granularity === selectedGranularity.value) {
        statistics.value = loadedStatistics;
      }
    } catch {
      if (request === activeRequest && granularity === selectedGranularity.value) {
        loadError.value = true;
      }
    } finally {
      if (request === activeRequest && granularity === selectedGranularity.value) {
        loading.value = false;
      }
    }
  }

  function retryLoading(): void {
    void loadStatistics(selectedGranularity.value);
  }

  watch(
    selectedGranularity,
    (granularity) => {
      void loadStatistics(granularity);
    },
    {immediate: true}
  );
</script>
