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

  const loginState = computed(() => {
    if (!info.value) {
      return e.LoginState.Unknown;
    }

    return info.value.userId ? e.LoginState.LoggedIn : e.LoginState.LoggedOut;
  });

  const loginConfirmed = computed(() => {
    return loginState.value === e.LoginState.LoggedIn;
  });

  const logoutConfirmed = computed(() => {
    return loginState.value === e.LoginState.LoggedOut;
  });

  function logout() {
    if (isSingleUserMode.value) {
      // In single user mode the user is always "logged in"
      return;
    }

    api.logout();

    // TODO: we may want to notify other tabs about logout event
  }

  return {
    userId,
    isSingleUserMode,
    loginState,
    loginConfirmed,
    logoutConfirmed,
    refreshAuthState,
    logout
  };
});
