import { computed, ref, watch } from "vue";
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

    const requiredTags = ref({});
    const excludedTags = ref({});

    function registerEntry(entry) {
        if (entry.id in entries.value) {
            if (entry.body === null && entries.value[entry.id].body !== null) {
                entry.body = entries.value[entry.id].body;
            }
        }

        entries.value[entry.id] = entry;
    }

    const loadedEntriesReport = computedAsync(async () => {
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

    const entriesReport = computedAsync(async () => {
        let report = loadedEntriesReport.value.slice();

        if (!globalSettings.showRead) {
            report = report.filter((entryId) => {
                return !entries.value[entryId].hasMarker(e.Marker.Read);
            });
        }

        report = report.filter((entryId) => {
            for (const tag of entries.value[entryId].tags) {
                if (excludedTags.value[tag]) {
                    return false;
                }
            }
            return true;
        });

        report = report.filter((entryId) => {
            for (const tag of Object.keys(requiredTags.value)) {
                if (requiredTags.value[tag] && !entries.value[entryId].tags.includes(tag)) {
                    return false;
                }
            }
            return true;
        });

        report = report.sort((a, b) => {
            const field = e.EntriesOrderProperties.get(globalSettings.entriesOrder).orderField;

            const entryA = entries.value[a];
            const entryB = entries.value[b];

            if (entryA[field] < entryB[field]) {
                return 1;
            }

            if (entryA[field] > entryB[field]) {
                return -1;
            }

            return 0;
        });

        return report;
    }, []);

    const reportTagsCount = computed(() => {
        const tagsCount = {};

        for (const entryId of entriesReport.value) {
            const entry = entries.value[entryId];

            for (const tag of entry.tags) {
                if (tag in tagsCount) {
                    tagsCount[tag] += 1;
                } else {
                    tagsCount[tag] = 1;
                }
            }
        }

        return tagsCount;
    });

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

    async function setMarker({entryId, marker}: {entryId: t.EntryId, marker: t.Marker}) {
        await api.setMarker({entryId: entryId, marker: marker});

        if (entryId in entries.value) {
            entries.value[entryId].setMarker(marker);
        }
    }

    async function removeMarker({entryId, marker}: {entryId: t.EntryId, marker: t.Marker}) {
        await api.removeMarker({entryId: entryId, marker: marker});

        if (entryId in entries.value) {
            entries.value[entryId].removeMarker(marker);
        }
    }

    function requireTag({tag}: {tag: string}) {
        requiredTags.value[tag] = true;
        excludedTags.value[tag] = false;
    }

    function excludeTag({tag}: {tag: string}) {
        excludedTags.value[tag] = true;
        requiredTags.value[tag] = false;
    }

    function resetTag({tag}: {tag: string}) {
        excludedTags.value[tag] = false;
        requiredTags.value[tag] = false;
    }

    return {
        entries,
        entriesReport,
        reportTagsCount,
        requestFullEntry,
        setMarker,
        removeMarker,
        requireTag,
        excludeTag,
        resetTag,
        requiredTags,
        excludedTags,
    };
});
