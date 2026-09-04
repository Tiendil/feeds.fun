<template>
  <side-panel-layout>
    <template #side-menu-item-1>
      Sorted by
      <config-selector
        :values="e.FeedsOrderProperties"
        v-model:property="globalSettings.feedsOrder" />
    </template>

    <template #side-menu-item-2>
      Show failed
      <config-flag
        v-model:flag="globalSettings.failedFeedsFirst"
        style="min-width: 2.5rem"
        on-text="first"
        off-text="last" />
    </template>

    <template #main-header>
      Feeds
      <span v-if="feedsState !== FeedsViewState.Loading"> [{{ sortedFeeds?.length }}] </span>
    </template>

    <ui-toolbar class="mb-2">
      <template #left>
        <toolbar-add-feed />

        <ui-button
          variant="secondary"
          size="compact"
          @click="goToImportOPML()">
          Import OPML
        </ui-button>
      </template>

      <template #right>
        <ui-button-link
          variant="secondary"
          size="compact"
          :href="api.downloadOPMLUrl"
          target="_blank">
          Export OPML
        </ui-button-link>
      </template>
    </ui-toolbar>

    <notifications
      v-if="feedsState === FeedsViewState.Empty"
      :create-rule-help="false"
      :api-key="false"
      :collections-notification_="true" />

    <feeds-list
      v-if="feedsState === FeedsViewState.Populated && sortedFeeds"
      :feeds="sortedFeeds" />

    <template #main-footer> </template>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import _ from "lodash";
  import {computed, provide} from "vue";
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useGlobalState} from "@/stores/globalState";
  import {useFeedsStore} from "@/stores/feeds";
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as navigation from "@/logic/navigation";

  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();
  const router = useRouter();

  const feedsStore = useFeedsStore();

  enum FeedsViewState {
    Loading = "loading",
    Empty = "empty",
    Populated = "populated"
  }

  provide("eventsViewName", "feeds");

  globalSettings.mainPanelMode = e.MainPanelMode.Feeds;

  function goToImportOPML() {
    router.push({
      name: e.MainPanelMode.Discovery,
      hash: `#${navigation.discoverySectionIds.importOPML}`
    });
  }

  const readyToUseSettings = computed(() => {
    return globalSettings.userSettingsPresent || !globalState.loginConfirmed;
  });

  const sortedFeeds = computed(() => {
    if (!readyToUseSettings.value) {
      return null;
    }

    let sorted = Object.values(feedsStore.feeds);

    if (sorted.length === 0) {
      return [];
    }

    const orderProperties = e.FeedsOrderProperties.get(globalSettings.feedsOrder as any);

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

  const feedsState = computed(() => {
    if (!readyToUseSettings.value || feedsStore.loadedFeedsReport === null) {
      return FeedsViewState.Loading;
    }

    if (sortedFeeds.value?.length === 0) {
      return FeedsViewState.Empty;
    }

    return FeedsViewState.Populated;
  });
</script>
