import { ref } from "vue";
import { defineStore } from "pinia";

import * as e from "@/logic/enums";

export const useGlobalSettingsStore = defineStore("globalSettings", () => {
    const mainPanelMode = ref(e.MainPanelMode.Entries);
    const lastEntriesPeriod = ref(e.LastEntriesPeriod.Month1);
    const entriesOrder = ref(e.EntriesOrder.score);

    return {
        mainPanelMode,
        lastEntriesPeriod,
        entriesOrder
    };
});
