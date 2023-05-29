import { ref, watch } from "vue";
import { useRouter } from 'vue-router'
import { defineStore } from "pinia";
import { computedAsync } from "@vueuse/core";
import { Timer } from "@/logic/timer";
import { useSupertokens } from "@/stores/supertokens";
import * as settings from "@/logic/settings";

import * as e from "@/logic/enums";

export const useGlobalState = defineStore("globalState", () => {
    const supertokens = useSupertokens();

    const tick = ref(1);

    async function doTick() {
        tick.value++;
    }

    const ticker = new Timer(doTick, 1000);

    ticker.start();

    const isLoggedIn = computedAsync(async () => {
        if (tick.value === 0) {
            // fake if to use tick in computed property
        }

        if (settings.authMode === settings.AuthMode.SingleUser) {
            return true;
        }

        return await supertokens.isLoggedIn();
    }, null);

    return {
        isLoggedIn,
    };
});
