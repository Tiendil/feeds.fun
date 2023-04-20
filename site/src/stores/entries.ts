import { ref, watch } from "vue";
import { useRouter } from 'vue-router'
import { defineStore } from "pinia";

import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import { Timer } from "@/logic/timer";
import { computedAsync } from "@vueuse/core";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

export const useEntriesStore = defineStore("entriesStore", () => {

    const globalSettings = useGlobalSettingsStore();

    const entries = ref({});
    const requestedEntries = ref({});

    function registerEntry(entry) {
        if (entry.id in entries.value) {
            if (entry.body === null && entries.value[entry.id].body !== null) {
                entry.body = entries.value[entry.id].body;
            }
        }
        entries.value[entry.id] = entry;
    }

    const entriesReport = computedAsync(async () => {
        const period = e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod).seconds;
        const loadedEntries = await api.getLastEntries({period: period,
                                                        dataVersion: globalSettings.dataVersion});

        const report = [];

        for (const entry of loadedEntries) {
            registerEntry(entry);
            report.push(entry.id);
        }

        return report;

    }, []);

    function requestFullEntry({entryId}: {entryId: t.EntryId}) {

        if (entryId in entries.value && entries.value[entryId].body !== null) {
            return;
        }

        requestedEntries.value[entryId] = true;
    }

    async function loadFullEntries() {
        const ids = Object.keys(requestedEntries.value);

        if (ids.length === 0) {
            return;
        }

        const entries = await api.getEntriesByIds({ids: ids});

        for (const entry of entries) {
            registerEntry(entry);
        }

        requestedEntries.value = {};
    }

    const requestedEntriesTimer = new Timer(loadFullEntries, 1000);

    requestedEntriesTimer.start();

    return {
        entries,
        entriesReport,
        requestFullEntry,
    };
});
