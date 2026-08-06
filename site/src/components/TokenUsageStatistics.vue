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
          <button
            v-for="[kind, resource] of tokenUsageResources"
            :key="kind"
            type="button"
            class="cursor-pointer hover:underline focus-visible:underline"
            :aria-pressed="visibleKinds[kind]"
            :title="tokenTypeTooltip(kind, resource.text)"
            @click="toggleTokenType(kind)">
            <span
              class="inline-block w-3 h-3 rounded-sm mr-1"
              :style="{backgroundColor: colorForResource(resource)}"
              aria-hidden="true"></span>
            <span :class="visibleKinds[kind] ? 'font-medium' : 'font-normal opacity-60'">
              {{ resource.text }}
            </span>
          </button>
        </div>
      </fieldset>

      <fieldset>
        <legend class="text-sm font-semibold mb-1">Range</legend>

        <div class="inline-flex overflow-hidden rounded-md border border-gray-300 text-sm">
          <button
            type="button"
            class="cursor-pointer px-3 py-1 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset"
            :class="
              !showAllTime
                ? 'bg-gray-100 font-medium text-gray-900'
                : 'bg-white font-normal text-gray-600 hover:bg-gray-50'
            "
            :aria-pressed="!showAllTime"
            :title="recentRangeTooltip"
            @click="showAllTime = false">
            Recent
          </button>

          <button
            type="button"
            class="cursor-pointer border-l border-gray-300 px-3 py-1 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset"
            :class="
              showAllTime
                ? 'bg-gray-100 font-medium text-gray-900'
                : 'bg-white font-normal text-gray-600 hover:bg-gray-50'
            "
            :aria-pressed="showAllTime"
            title="Show all available history"
            @click="showAllTime = true">
            All time
          </button>
        </div>
      </fieldset>
    </div>

    <div
      v-if="loadError"
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

    <div
      class="relative border border-gray-200 rounded-lg"
      :aria-busy="loading">
      <div class="h-64 w-full p-2">
        <ChartBar
          role="img"
          :aria-label="rangeLabel"
          :data="chartData"
          :options="chartOptions" />
      </div>

      <div
        v-if="chartOverlayMessage !== null"
        class="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75"
        role="status"
        aria-live="polite">
        {{ chartOverlayMessage }}
      </div>
    </div>

    <p class="mt-1 text-xs text-gray-500">{{ rangeLabel }}</p>
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
    emptyTokenUsageStatistics,
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

  type DisplayedStatistics = {
    readonly granularity: TokenUsageTimeGranularity;
    readonly data: TokenUsageStatisticsData;
  };

  const initialGranularity = e.TimeGranularity.Day;
  const selectedGranularity = ref<TokenUsageTimeGranularity>(initialGranularity);
  const showAllTime = ref(false);
  const visibleKinds = reactive<Record<TokenUsageResourceKind, boolean>>({
    [e.ResourceKind.DayTokenUsage]: true,
    [e.ResourceKind.MonthTokenUsage]: true,
    [e.ResourceKind.LifetimeTokenUsage]: true
  });
  const displayedStatistics = shallowRef<DisplayedStatistics>({
    granularity: initialGranularity,
    data: emptyTokenUsageStatistics(initialGranularity, new Date())
  });
  const loading = ref(false);
  const loadError = ref(false);
  const statisticsCache = new Map<TokenUsageTimeGranularity, TokenUsageStatisticsData>();
  let activeRequest = 0;

  const visibleTokenUsageResources = computed(() => tokenUsageResources.filter(([kind]) => visibleKinds[kind]));
  const chartOverlayMessage = computed(() => {
    if (loading.value) {
      return "Loading...";
    }

    if (visibleTokenUsageResources.value.length === 0) {
      return "Select at least one token type to display.";
    }

    return null;
  });
  const displayedGranularity = computed(() => displayedStatistics.value.granularity);

  const dateRange = computed(() => {
    const granularity = displayedGranularity.value;
    const lastDate = periodStart(new Date(), granularity);
    const windowSize = e.windowSizes.get(granularity)!;
    const recentFirstDate = shiftDate(lastDate, 1 - windowSize, granularity);
    const loadedStatistics = displayedStatistics.value.data;

    if (!showAllTime.value) {
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

  const slots = computed(() =>
    tokenUsageSlots({
      statistics: displayedStatistics.value.data,
      granularity: displayedGranularity.value,
      firstDate: dateRange.value.firstDate,
      lastDate: dateRange.value.lastDate
    })
  );

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

  function toggleTokenType(kind: TokenUsageResourceKind): void {
    visibleKinds[kind] = !visibleKinds[kind];
  }

  function tokenTypeTooltip(kind: TokenUsageResourceKind, text: string): string {
    if (visibleKinds[kind]) {
      return `Hide ${text} from the plot`;
    }

    return `Show ${text} on the plot`;
  }

  function colorForResource(resource: e.ResourceKindProperty): string {
    if (resource.plotColor === undefined || !(resource.plotColor in plotColors.tokenUsage)) {
      throw new Error("Resource kind does not define a plot color");
    }

    return plotColors.tokenUsage[resource.plotColor as keyof typeof plotColors.tokenUsage];
  }

  const chartData = computed<ChartData<"bar", number[], string>>(() => ({
    labels: slots.value.map((slot) => formatPeriod(slot.date, displayedGranularity.value)),
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
          maxTicksLimit: displayedGranularity.value === e.TimeGranularity.Day ? 10 : 12
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

  const rangeLabel = computed(() => {
    if (slots.value.length === 0) {
      return "Token usage history";
    }

    const firstDate = formatPeriod(slots.value[0].date, displayedGranularity.value);
    const lastDate = formatPeriod(slots.value[slots.value.length - 1].date, displayedGranularity.value);
    const granularityText = e.TimeGranularityProperties.get(displayedGranularity.value)!.text;
    const granularityLabel = granularityText.charAt(0).toUpperCase() + granularityText.slice(1);

    return `${granularityLabel} token usage from ${firstDate} to ${lastDate}`;
  });

  const recentRangeTooltip = computed(
    () => `Show the last ${e.windowSizes.get(displayedGranularity.value)!} ${displayedGranularity.value}s`
  );

  async function loadStatistics(granularity: TokenUsageTimeGranularity): Promise<void> {
    const request = ++activeRequest;
    const cachedStatistics = statisticsCache.get(granularity);

    if (cachedStatistics !== undefined) {
      displayedStatistics.value = {granularity, data: cachedStatistics};
      loading.value = false;
      loadError.value = false;
      return;
    }

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
        displayedStatistics.value = {granularity, data: loadedStatistics};
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
