<template>
<entries-list :entries="sortedEntries"/>
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

const globalSettings = useGlobalSettingsStore();

const entries = computedAsync(async () => {
    return await api.getEntries({period: e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod).seconds});
}, null);


const sortedEntries = computed(() => {
    if (entries.value === null) {
        return null;
    }

    return entries.value.slice().sort((a, b) => {
        const field = e.EntriesOrderProperties.get(globalSettings.entriesOrder).field;

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
