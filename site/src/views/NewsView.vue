<template>
<h2>
  News

  <span v-if="entriesNumber > 0">[{{entriesNumber}}]</span>
</h2>

<entries-list :entriesIds="entriesStore.entriesReport"
              :time-field="timeField"
              :show-tags="globalSettings.showEntriesTags"
              :showFromStart=100
              :showPerPage=50
              />
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import { useEntriesStore } from "@/stores/entries";

const globalSettings = useGlobalSettingsStore();
const entriesStore = useEntriesStore();

globalSettings.mainPanelMode = e.MainPanelMode.Entries;

const entriesNumber = computed(() => {
    return entriesStore.entriesReport.length;
});

const timeField = computed(() => {
    return e.EntriesOrderProperties.get(globalSettings.entriesOrder).timeField;
});

</script>

<style></style>
