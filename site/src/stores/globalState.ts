import {ref, watch, computed} from "vue";
import {useRouter, useRoute} from "vue-router";
import {defineStore} from "pinia";
import {computedAsync, useBroadcastChannel} from "@vueuse/core";

import {Timer} from "@/logic/timer";
import * as settings from "@/logic/settings";
import * as api from "@/logic/api";
import * as e from "@/logic/enums";

const GLOBAL_BROADCAST_CHANNEL_ID = "ffun-global-event-channel";
const GLOBAL_BROADCAST_EVENT_LOGOUT_COMPLETED = "logoutCompleted";

const LOGGED_OUT_QUERY_MARKER = "logged-out";

export const useGlobalState = defineStore("globalState", () => {
  const router = useRouter();
  const route = useRoute();

  const infoRefreshMarker = ref(0);

  function refreshAuthState() {
    infoRefreshMarker.value++;
  }

  ////////////////////////////////
  // sync login state between tabs
  ////////////////////////////////
  const globalChannel = useBroadcastChannel<any>({ name: GLOBAL_BROADCAST_CHANNEL_ID });

  watch(globalChannel.data, (event) => {
    if (event.type === GLOBAL_BROADCAST_EVENT_LOGOUT_COMPLETED) {
      refreshAuthState();
    }
  });

  // check if the marker is in the URL (means that user has just redirected after logout)
  watch(route, (r) => {
    if (!(LOGGED_OUT_QUERY_MARKER in r.query)) {
      return;
    }

    globalChannel.post({ type: GLOBAL_BROADCAST_EVENT_LOGOUT_COMPLETED });

    // remove the marker from the URL
    const query = { ...r.query };
    delete query[LOGGED_OUT_QUERY_MARKER];
    router.replace({ query });
  });
  ////////////////////////////////

  // Periodic check auth state by timer
  const authStateRefresher = new Timer(refreshAuthState, settings.authRefreshInterval);

  // Check auth state on the particular events
  window.addEventListener("focus", refreshAuthState);
  window.addEventListener("online", refreshAuthState);
  window.addEventListener("visibilitychange", refreshAuthState);
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      // BFCache restore (the user goes Back/Forward and the browser instantly revives a frozen snapshot).
      refreshAuthState();
    }
  });

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

  const loginUnknown = computed(() => {
    return loginState.value === e.LoginState.Unknown;
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

    api.logoutRedirect();

    // TODO: we may want to notify other tabs about logout event
  }

  return {
    userId,
    isSingleUserMode,
    loginState,
    loginUnknown,
    loginConfirmed,
    logoutConfirmed,
    refreshAuthState,
    logout,
  };
});
