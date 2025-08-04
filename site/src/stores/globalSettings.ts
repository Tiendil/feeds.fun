import _ from "lodash";
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
  // const lastEntriesPeriod = ref(e.LastEntriesPeriod.Day3);
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

  function backgroundSetUserSetting(kind, value) {
    api.setUserSetting({kind: kind, value: value}).catch((error) => {
      console.error(`Error in API call setUserSetting for kind "${kind}":`, error);
    });
  }

  function backendSettings(kind, validator, defaultValue) {
    return computed({
      get() {
        if (!userSettings.value) {
          // TODO: should we return null here?
          //       currently the "null" value causes warning on ConfigSelector.vue
          return "";
        }

        const setting = userSettings.value[kind];

        if (!validator(setting.value)) {
          // initiate async API call to set default value
          // TODO: is it ok?
          backgroundSetUserSetting(kind, defaultValue);
          return defaultValue;
        }

        return setting.value;
      },

      async set(newValue) {
        userSettings.value[kind].value = newValue;
        backgroundSetUserSetting(kind, newValue);

        // TODO: does we need it here?
        updateDataVersion();
      }
    });

  }

  const lastEntriesPeriod = backendSettings(
    "view_news_filter_interval",
    (rawValue) => { return _.findKey(e.LastEntriesPeriod, (value) => value === rawValue); },
    e.LastEntriesPeriod.Day3
  );

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
