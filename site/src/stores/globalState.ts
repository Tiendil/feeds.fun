import {ref, watch, computed} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";
import {computedAsync} from "@vueuse/core";

import {Timer} from "@/logic/timer";
import * as settings from "@/logic/settings";
import * as api from "@/logic/api";
import * as e from "@/logic/enums";

export const useGlobalState = defineStore("globalState", () => {

  const infoRefreshMarker = ref(0);

  function refreshAuthState() {
    infoRefreshMarker.value++;
  }

  const authStateRefresher = new Timer(refreshAuthState, settings.authRefreshInterval);

  const info = computedAsync(async () => {
    infoRefreshMarker.value;
    return await api.getInfo();
  }, null);

  const userId = computed(() => {
    return info.value ? info.value.userId : null;
  });

  const isSingleUserMode = computed(() => {
    return info.value ? info.value.singleUserMode : false;
  });

  const isLoggedIn = computed(() => {
    return userId.value !== null;
  });

  function logout() {
    // TODO: implement

    // if (isSingleUserMode.value) {
    //   return;
    // }
    // await Session.signOut();
    // refreshAuthState();
    // router.push({name: "Home"});
  }

  return {
    userId,
    isSingleUserMode,
    isLoggedIn,
    refreshAuthState,
    logout
  };
});
