<template>
  <tr>
    <td>{{ period }}</td>
    <td style="text-align: right">
      <app-tooltip :text="fullValue(properties.usage.used, ' USD')">
        <span
          class="cursor-help rounded-sm tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          tabindex="0">
          {{ cost_used }}
        </span>
      </app-tooltip>
    </td>
    <td style="text-align: right">
      <app-tooltip :text="fullValue(properties.usage.reserved, ' USD')">
        <span
          class="cursor-help rounded-sm tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          tabindex="0">
          {{ cost_reserved }}
        </span>
      </app-tooltip>
    </td>
    <td style="text-align: right">
      <app-tooltip :text="fullValue(properties.usage.total(), ' USD')">
        <span
          class="cursor-help rounded-sm tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          tabindex="0">
          {{ cost_total }}
        </span>
      </app-tooltip>
    </td>
    <td style="text-align: right">
      <app-tooltip :text="percents_full">
        <span
          class="cursor-help rounded-sm tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          tabindex="0">
          {{ percents }}%
        </span>
      </app-tooltip>
    </td>
  </tr>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const properties = defineProps<{
    usage: t.ResourceHistoryRecord;
  }>();

  const globalSettings = useGlobalSettingsStore();

  const period = computed(() => {
    return properties.usage.intervalStartedAt.toLocaleString("default", {month: "long", year: "numeric"});
  });

  const digits = 2;
  const multiplier = 10 ** digits;

  const percent = computed<number | null>(() => {
    if (!globalSettings.userSettingsPresent) {
      return null;
    }

    const setting = globalSettings.max_tokens_cost_in_month;

    if (!setting) {
      return null;
    }

    if (typeof setting.value !== "number") {
      return null;
    }

    const limit: number = setting.value;
    const total = properties.usage.total();

    if (limit == 0) {
      return null;
    }

    return (total / limit) * 100;
  });

  const percents = computed(() => (percent.value === null ? "—" : roundUp(percent.value)));
  const percents_full = computed(() => (percent.value === null ? "" : fullValue(percent.value, "%")));

  const cost_used = computed(() => {
    return roundUp(properties.usage.used);
  });

  const cost_reserved = computed(() => {
    return roundUp(properties.usage.reserved);
  });

  const cost_total = computed(() => {
    return roundUp(properties.usage.total());
  });

  function roundUp(value: number): string {
    const scaled = value * multiplier;
    const floatingPointTolerance = Number.EPSILON * Math.max(1, Math.abs(scaled));

    return (Math.ceil(scaled - floatingPointTolerance) / multiplier).toFixed(digits);
  }

  function fullValue(value: number, suffix: string): string {
    return `${value}${suffix}`;
  }
</script>

<style></style>
