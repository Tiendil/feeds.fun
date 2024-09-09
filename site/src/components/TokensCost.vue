<template>
  <tr>
    <td>{{ period }}</td>
    <td style="text-align: right">{{ cost_used }}</td>
    <td style="text-align: right">{{ cost_reserved }}</td>
    <td style="text-align: right">{{ cost_total }}</td>
    <td style="text-align: right">{{ percents }}%</td>
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

  globalSettings.mainPanelMode = e.MainPanelMode.Settings;

  const period = computed(() => {
    return properties.usage.intervalStartedAt.toLocaleString("default", {month: "long", year: "numeric"});
  });

  const k = 2;

  const percents = computed(() => {
    if (globalSettings.userSettings == null) {
      return "—";
    }

    const setting = globalSettings.userSettings["max_tokens_cost_in_month"];

    if (!setting) {
      return "—";
    }

    if (typeof setting.value !== "number") {
      return "—";
    }

    const limit: number = setting.value;
    const total = properties.usage.total();

    if (limit == 0) {
      return "—";
    }

    return ((total / limit) * 100).toFixed(k);
  });

  const cost_used = computed(() => {
    return properties.usage.used.toFixed(k);
  });

  const cost_reserved = computed(() => {
    return properties.usage.reserved.toFixed(k);
  });

  const cost_total = computed(() => {
    return properties.usage.total().toFixed(k);
  });
</script>

<style></style>
