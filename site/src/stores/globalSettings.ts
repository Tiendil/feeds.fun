import { ref, watch } from "vue";
import { useRouter } from 'vue-router'
import { defineStore } from "pinia";

import * as e from "@/logic/enums";

export const useGlobalSettingsStore = defineStore("globalSettings", () => {

    const router = useRouter();

    const mainPanelMode = ref(e.MainPanelMode.Entries);
    const lastEntriesPeriod = ref(e.LastEntriesPeriod.Month1);
    const entriesOrder = ref(e.EntriesOrder.Score);
    const showEntriesTags = ref(true);
    const showRead = ref(true);
    const dataVersion = ref(0);

    watch(mainPanelMode, (newValue, oldValue) => {
        router.push({ name: mainPanelMode.value, params: {} });
    });

    return {
        mainPanelMode,
        lastEntriesPeriod,
        entriesOrder,
        showEntriesTags,
        showRead,
        dataVersion
    };
});
