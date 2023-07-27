<template>
<tr>
  <td>{{ period }}</td>
  <td style="text-align: right">{{ usage.used }}</td>
  <td style="text-align: right">{{ usage.reserved }}</td>
  <td style="text-align: right">{{ usage.total() }}</td>
  <td style="text-align: right">{{ percents }}%</td>
</tr>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const properties = defineProps<{
    usage: t.ResourceHistoryRecord;
  }>();

  const globalSettings = useGlobalSettingsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Settings;

  const openAIUsage = computedAsync(async () => {
    return await api.getResourceHistory({kind: "openai_tokens"});
  }, null);

  const period = computed(() => {
      return properties.usage.intervalStartedAt.toLocaleString("default", {month: "long", year: "numeric"});
  });

  const percents = computed(() => {
      if (globalSettings.userSettings == null) {
        return "—";
    }

    const setting = globalSettings.userSettings["openai_max_tokens_in_month"];

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

    return ((total / limit) * 100).toFixed(5);
  });

</script>

<style></style>
