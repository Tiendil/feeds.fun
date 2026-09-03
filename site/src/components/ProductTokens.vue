<template>
  <div
    v-if="productState !== null"
    class="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-xs text-slate-700">
    <span class="font-medium text-slate-500">Tokens available</span>

    <app-tooltip
      v-for="item of tokenItems"
      :key="item.kind"
      placement="bottom-end">
      <div
        class="flex cursor-help items-baseline gap-1 whitespace-nowrap rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        tabindex="0">
        <span
          class="inline-block h-2 w-2 rounded-full"
          :style="{backgroundColor: item.color}"></span>
        <span>{{ item.text }}</span>
        <span class="font-semibold tabular-nums text-slate-900">
          {{ formatAmount(item.token.balance) }}
        </span>
      </div>

      <template #content>
        <div class="font-medium">{{ item.description }}</div>
        <div>{{ availabilityText(item) }}</div>
        <div
          v-if="refillText(item) !== null"
          class="text-slate-300">
          {{ refillText(item) }}
        </div>
      </template>
    </app-tooltip>
  </div>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import {computedAsync} from "@vueuse/core";

  import * as api from "@/logic/api";
  import * as e from "@/logic/enums";
  import {getPlotColors} from "@/logic/plots";
  import {tokenUsageResourceKinds, type TokenUsageResourceKind} from "@/logic/resourceStatistics";
  import type * as t from "@/logic/types";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useGlobalState} from "@/stores/globalState";

  const entriesStore = useEntriesStore();
  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();

  const productState = computedAsync(async () => {
    globalSettings.dataVersion;
    entriesStore.entriesLoadRevision;

    if (!globalState.loginConfirmed) {
      return null;
    }

    return await api.getProductState();
  }, null);

  type TokenItem = {
    readonly kind: TokenUsageResourceKind;
    readonly text: string;
    readonly description: string;
    readonly color: string;
    readonly token: t.ProductStateToken;
  };

  const plotColors = getPlotColors();
  const numberFormatter = new Intl.NumberFormat("en-US");
  const refillDateFormatter = new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeZone: "UTC"
  });
  const refillTimeFormatter = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "UTC"
  });

  const tokenItems = computed<TokenItem[]>(() => {
    const state = productState.value;

    if (state === null) {
      return [];
    }

    return tokenUsageResourceKinds.map((kind) => {
      const resource = e.ResourceKindProperties.get(kind)!;

      if (resource.plotColor === undefined || !(resource.plotColor in plotColors.tokenUsage)) {
        throw new Error("Token usage resource does not define a plot color");
      }

      return {
        kind,
        text: resource.shortText ?? resource.text,
        description: resource.text,
        color: plotColors.tokenUsage[resource.plotColor as keyof typeof plotColors.tokenUsage],
        token: state.tokens[kind]
      };
    });
  });

  function formatAmount(amount: number): string {
    return numberFormatter.format(amount);
  }

  function isRecurring(item: TokenItem): boolean {
    return item.kind !== e.ResourceKind.LifetimeTokenUsage;
  }

  function hasRecurringLimit(item: TokenItem): boolean {
    return isRecurring(item) && item.token.limit !== null;
  }

  function recurringLimit(item: TokenItem): number {
    return item.token.limit ?? 0;
  }

  function availabilityText(item: TokenItem): string {
    if (isRecurring(item) && !hasRecurringLimit(item)) {
      return "Not currently available";
    }

    const available = `${formatAmount(item.token.balance)} available`;

    if (!hasRecurringLimit(item)) {
      return available;
    }

    return `${available} · ${formatAmount(recurringLimit(item))}-token limit`;
  }

  function refillText(item: TokenItem): string | null {
    if (isRecurring(item) && !hasRecurringLimit(item)) {
      return null;
    }

    if (item.token.periodEndsAt === null) {
      return "Available until used";
    }

    return `Refills ${refillDateFormatter.format(item.token.periodEndsAt)} at ${refillTimeFormatter.format(item.token.periodEndsAt)} UTC`;
  }
</script>
