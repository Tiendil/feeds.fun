import {ref, computed} from "vue";
import {defineStore} from "pinia";
import {computedAsync} from "@vueuse/core";
import {useGlobalState} from "@/stores/globalState";

import * as e from "@/logic/enums";
import * as api from "@/logic/api";

export const useGlobalSettingsStore = defineStore("globalSettings", () => {
  const globalState = useGlobalState();

  // General
  const mainPanelMode = ref(e.MainPanelMode.Entries);
  const dataVersion = ref(0);
  const showSidebar = ref(true);
  const showSidebarPoint = ref(false);

  // Entries
  const lastEntriesPeriod = ref(e.LastEntriesPeriod.Day3);
  const entriesOrder = ref(e.EntriesOrder.Score);
  const minTagCount = ref(e.MinNewsTagCount.Two);
  const showRead = ref(true);

  const entriesOrderProperties = computed(() => {
    return e.EntriesOrderProperties.get(entriesOrder.value);
  });

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
    minTagCount,
    showRead,
    entriesOrderProperties,
    dataVersion,
    updateDataVersion,
    showFeedsDescriptions,
    userSettings,
    info,
    feedsOrder,
    failedFeedsFirst,
    rulesOrder,
    showSidebar,
    showSidebarPoint
  };
});
