import {ref, watch} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";
import {computedAsync} from "@vueuse/core";
import {useGlobalState} from "@/stores/globalState";

import * as e from "@/logic/enums";
import * as api from "@/logic/api";

export const useGlobalSettingsStore = defineStore("globalSettings", () => {
  const router = useRouter();
  const globalState = useGlobalState();

  // General
  const mainPanelMode = ref(e.MainPanelMode.Entries);
  const dataVersion = ref(0);

  // Entries
  const lastEntriesPeriod = ref(e.LastEntriesPeriod.Day3);
  const entriesOrder = ref(e.EntriesOrder.Score);
  const showRead = ref(true);

  // Feeds
  const showFeedsDescriptions = ref(true);
  const feedsOrder = ref(e.FeedsOrder.Title);
  const failedFeedsFirst = ref(false);

  // Rules
  const rulesOrder = ref(e.RulesOrder.Tags);

  function updateDataVersion() {
    dataVersion.value++;
  }

  // backend side settings
  const userSettings = computedAsync(async () => {
    if (!globalState.isLoggedIn) {
      return null;
    }

    // force refresh
    dataVersion.value;

    return await api.getUserSettings();
  }, null);

  const info = computedAsync(async () => {
    if (!globalState.isLoggedIn) {
      return null;
    }

    // force refresh
    dataVersion.value;

    return await api.getInfo();
  }, null);

  return {
    mainPanelMode,
    lastEntriesPeriod,
    entriesOrder,
    showRead,
    dataVersion,
    updateDataVersion,
    showFeedsDescriptions,
    userSettings,
    info,
    feedsOrder,
    failedFeedsFirst,
    rulesOrder
  };
});
