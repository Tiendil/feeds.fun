<template>
<entries-list :entries="displayedEntries"
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

const globalSettings = useGlobalSettingsStore();

globalSettings.mainPanelMode = e.MainPanelMode.Entries;

const entries = computedAsync(async () => {
    return await api.getLastEntries({period: e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod).seconds});
}, null);


const timeField = computed(() => {
    return e.EntriesOrderProperties.get(globalSettings.entriesOrder).timeField;
});

const displayedEntries = computed(() => {
    if (entries.value === null) {
        return null;
    }

    let processedEntries = entries.value.slice();

    if (!globalSettings.showRead) {
        processedEntries = processedEntries.filter((entry) => {
            return !entry.markers.includes(e.Marker.Read);
        });
    }

    return processedEntries.sort((a, b) => {
        const field = e.EntriesOrderProperties.get(globalSettings.entriesOrder).orderField;

        if (a[field] < b[field]) {
            return 1;
        }

        if (a[field] > b[field]) {
            return -1;
        }

        return 0;
    });
});

</script>

<style></style>
