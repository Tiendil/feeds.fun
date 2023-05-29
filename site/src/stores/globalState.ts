import { ref, watch, computed } from "vue";
import { useRouter } from 'vue-router'
import { defineStore } from "pinia";
import { useSupertokens } from "@/stores/supertokens";
import * as settings from "@/logic/settings";

import * as e from "@/logic/enums";

export const useGlobalState = defineStore("globalState", () => {
    const supertokens = useSupertokens();

    const isLoggedIn = computed(() => {
        if (settings.authMode === settings.AuthMode.SingleUser) {
            return true;
        }

        return supertokens.isLoggedIn;
    });

    return {
        isLoggedIn,
    };
});
