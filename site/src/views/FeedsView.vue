<template>
  <side-panel-layout>
    <template #side-menu-item-1>
      Show descriptions:
      <config-flag
        v-model:flag="globalSettings.showFeedsDescriptions"
        on-text="yes"
        off-text="no" />
    </template>

    <template #side-menu-item-2>
      Sorted by
      <config-selector
        :values="e.FeedsOrderProperties"
        v-model:property="globalSettings.feedsOrder" />
    </template>

    <template #side-menu-item-3>
      Show failed
      <config-flag
        v-model:flag="globalSettings.failedFeedsFirst"
        on-text="first"
        off-text="last" />
    </template>

    <template #main-header>
      Feeds
      <span v-if="sortedFeeds"> [{{ sortedFeeds.length }}] </span>
    </template>

    <template #main-footer> </template>

    <feeds-list :feeds="sortedFeeds" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";

  const globalSettings = useGlobalSettingsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Feeds;

  const feeds = computedAsync(async () => {
    return await api.getFeeds({dataVersion: globalSettings.dataVersion});
  }, null);

  const sortedFeeds = computed(() => {
    if (!feeds.value) {
      return null;
    }

    let sorted = feeds.value.slice();

    const orderProperties = e.FeedsOrderProperties.get(globalSettings.feedsOrder);

    const orderField = orderProperties.orderField;

    const direction = {asc: -1, desc: 1}[orderProperties.orderDirection];

    sorted = sorted.sort((a, b) => {
      if (a.isOk && !b.isOk) {
        if (globalSettings.failedFeedsFirst) {
          return 1;
        }
        return -1;
      }

      if (!a.isOk && b.isOk) {
        if (globalSettings.failedFeedsFirst) {
          return -1;
        }
        return 1;
      }

      const valueA = a[orderField];
      const valueB = b[orderField];

      if (valueA < valueB) {
        return 1 * direction;
      }

      if (valueA > valueB) {
        return -1 * direction;
      }

      return 0;
    });

    return sorted;
  }, null);
</script>

<style></style>
