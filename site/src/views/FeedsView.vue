<template>
  <side-panel-layout>
    <template #side-menu-item-1>
      Show descriptions:
      <config-flag
        style="min-width: 2.5rem"
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
        style="min-width: 2.5rem"
        on-text="first"
        off-text="last" />
    </template>

    <template #side-menu-item-4>
      <a
        class="ffun-form-button p-1 my-1 block w-full text-center"
        href="/api/get-opml"
        target="_blank"
        >Download OPML</a
      >
    </template>

    <template #main-header>
      Feeds
      <span v-if="sortedFeeds"> [{{ sortedFeeds.length }}] </span>
    </template>

    <notifications
      v-if="sortedFeeds !== null"
      :create-rule-help="false"
      :api-key="false"
      :collections-notification_="sortedFeeds === null || sortedFeeds.length == 0"
      :collections-warning_="true" />

    <feeds-list
      v-if="sortedFeeds"
      :feeds="sortedFeeds" />

    <template #main-footer> </template>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import _ from "lodash";
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useFeedsStore} from "@/stores/feeds";
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";

  const globalSettings = useGlobalSettingsStore();

  const feedsStore = useFeedsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Feeds;

  const sortedFeeds = computed(() => {
    let sorted = Object.values(feedsStore.feeds);

    if (sorted.length === 0) {
      return [];
    }

    const orderProperties = e.FeedsOrderProperties.get(globalSettings.feedsOrder);

    if (!orderProperties) {
      throw new Error(`Invalid order properties: ${globalSettings.feedsOrder}`);
    }

    const orderField = orderProperties.orderField;

    const direction = {asc: -1, desc: 1}[orderProperties.orderDirection];

    if (direction === undefined) {
      throw new Error(`Invalid order direction: ${orderProperties.orderDirection}`);
    }

    sorted = sorted.sort((a: t.Feed, b: t.Feed) => {
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

      const valueA = _.get(a, orderField, null);
      const valueB = _.get(b, orderField, null);

      if (valueA === null && valueB === null) {
        return 0;
      }

      if (valueA === null) {
        return 1 * direction;
      }

      if (valueB === null) {
        return -1 * direction;
      }

      if (valueA < valueB) {
        return 1 * direction;
      }

      if (valueA > valueB) {
        return -1 * direction;
      }

      return 0;
    });

    return sorted;
  });
</script>
