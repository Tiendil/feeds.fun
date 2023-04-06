import { ref } from "vue";
import { defineStore } from "pinia";

import * as e from "@/logic/enums";

export const useGlobalSettingsStore = defineStore("globalSettings", () => {
    const mainPanelMode = ref(e.MainPanelMode.News);

    return {
        mainPanelMode
    };
});
