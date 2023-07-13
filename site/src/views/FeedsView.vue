<template>
<side-panel-layout>
  <template #side-menu-item-1>
    Show descriptions: <config-flag v-model:flag="globalSettings.showFeedsDescriptions"
                                    on-text="yes"
                                    off-text="no"/>
  </template>

  <template #side-menu-item-2>
    Sorted by
    <config-selector :values="e.FeedsOrderProperties"
                     v-model:property="globalSettings.feedsOrder"/>
  </template>

  <template #side-menu-item-3>
    Show failed
    <config-flag v-model:flag="globalSettings.failedFeedsFirst"
                 on-text="first"
                 off-text="last"/>
  </template>

  <template #main-header>
    Feeds
    <span v-if="sortedFeeds">
      [{{ sortedFeeds.length }}]
    </span>
  </template>

  <template #main-footer>
  </template>

  <feeds-list :feeds="sortedFeeds" />
</side-panel-layout>

</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import { useGlobalSettingsStore } from "@/stores/globalSettings";
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

    sorted = sorted.sort((a, b) => {
        const field = e.FeedsOrderProperties.get(globalSettings.feedsOrder).orderField;

        const valueA = a[field];
        const valueB = b[field];

        if (valueA < valueB) {
            return 1;
        }

        if (valueA > valueB) {
            return -1;
        }

        return 0;
    });

    return sorted;
}, null);

</script>

<style></style>
