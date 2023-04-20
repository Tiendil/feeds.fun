<template>
<h2>
  News

  <span v-if="displayedEntries.length > 0">[{{displayedEntries.length}}]</span>
</h2>

<entries-list :entriesIds="displayedEntries"
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

const timeField = computed(() => {
    return e.EntriesOrderProperties.get(globalSettings.entriesOrder).timeField;
});

const displayedEntries = computed(() => {
    const entries = entriesStore.entries;

    let processedEntries = entriesStore.entriesReport.slice();

    if (!globalSettings.showRead) {
        processedEntries = processedEntries.filter((entryId) => {
            return !entries[entryId].hasMarker(e.Marker.Read);
        });
    }

    return processedEntries.sort((a, b) => {
        const field = e.EntriesOrderProperties.get(globalSettings.entriesOrder).orderField;

        const entryA = entries[a];
        const entryB = entries[b];

        if (entryA[field] < entryB[field]) {
            return 1;
        }

        if (entryA[field] > entryB[field]) {
            return -1;
        }

        return 0;
    });
});

</script>

<style></style>
