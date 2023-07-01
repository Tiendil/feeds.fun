import { ref, watch } from "vue";
import { useRouter } from 'vue-router'
import { defineStore } from "pinia";
import { computedAsync } from "@vueuse/core";

import * as e from "@/logic/enums";
import * as api from "@/logic/api";

export const useGlobalSettingsStore = defineStore("globalSettings", () => {

    const router = useRouter();

    // General
    const mainPanelMode = ref(e.MainPanelMode.Entries);
    const dataVersion = ref(0);

    // Entries
    const lastEntriesPeriod = ref(e.LastEntriesPeriod.Day1);
    const entriesOrder = ref(e.EntriesOrder.Score);
    const showEntriesTags = ref(true);
    const showRead = ref(true);

    // Feeds
    const showFeedsDescriptions = ref(true);

    watch(mainPanelMode, (newValue, oldValue) => {
        router.push({ name: mainPanelMode.value, params: {} });
    });

    function updateDataVersion() {
        dataVersion.value++;
    }

    // backend side settings
    const userSettings = computedAsync(async () => {
        return await api.getUserSettings();
    }, null);

    return {
        mainPanelMode,
        lastEntriesPeriod,
        entriesOrder,
        showEntriesTags,
        showRead,
        dataVersion,
        updateDataVersion,
        showFeedsDescriptions,
        userSettings
    };
});
