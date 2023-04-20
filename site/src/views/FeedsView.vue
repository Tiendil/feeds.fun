<template>
  <h2>
    Feeds
    <span v-if="feeds">
      [{{ feeds.length }}]
    </span>
  </h2>
<feeds-list :feeds="feeds" />
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

</script>

<style></style>
