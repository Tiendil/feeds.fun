<template>
  <div class="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-xs text-slate-700">
    <span class="font-medium text-slate-500">Tokens left</span>

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
        <div>
          {{ formatAmount(item.token.balance) }} left
          <template v-if="hasRecurringLimit(item)"> · {{ formatAmount(recurringLimit(item)) }} limit </template>
        </div>
        <div class="text-slate-300">{{ resetText(item) }}</div>
      </template>
    </app-tooltip>
  </div>
</template>

<script lang="ts" setup>
  import {computed} from "vue";

  import * as e from "@/logic/enums";
  import {getPlotColors} from "@/logic/plots";
  import {tokenUsageResourceKinds, type TokenUsageResourceKind} from "@/logic/resourceStatistics";
  import type * as t from "@/logic/types";

  const properties = defineProps<{
    tokens: t.ProductState["tokens"];
  }>();

  type TokenItem = {
    readonly kind: TokenUsageResourceKind;
    readonly text: string;
    readonly description: string;
    readonly color: string;
    readonly token: t.ProductStateToken;
  };

  const plotColors = getPlotColors();
  const numberFormatter = new Intl.NumberFormat("en-US");
  const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short"
  });

  const tokenItems = computed<TokenItem[]>(() =>
    tokenUsageResourceKinds.map((kind) => {
      const resource = e.ResourceKindProperties.get(kind)!;

      if (resource.plotColor === undefined || !(resource.plotColor in plotColors.tokenUsage)) {
        throw new Error("Token usage resource does not define a plot color");
      }

      return {
        kind,
        text: resource.shortText ?? resource.text,
        description: resource.text,
        color: plotColors.tokenUsage[resource.plotColor as keyof typeof plotColors.tokenUsage],
        token: properties.tokens[kind]
      };
    })
  );

  function formatAmount(amount: number): string {
    return numberFormatter.format(amount);
  }

  function hasRecurringLimit(item: TokenItem): boolean {
    return item.kind !== e.ResourceKind.LifetimeTokenUsage;
  }

  function recurringLimit(item: TokenItem): number {
    return item.token.limit ?? 0;
  }

  function resetText(item: TokenItem): string {
    if (item.token.periodEndsAt === null) {
      return "Does not reset";
    }

    return `Resets ${dateTimeFormatter.format(item.token.periodEndsAt)}`;
  }
</script>
