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

  // Feeds
  const showFeedsDescriptions = ref(true);
  const feedsOrder = ref(e.FeedsOrder.Title);
  const failedFeedsFirst = ref(false);

  // Rules
  const rulesOrder = ref(e.RulesOrder.Tags);

  function updateDataVersion() {
    dataVersion.value++;
  }

  // TODO: do we need this data after all refactorings with user settings?
  const info = computedAsync(async () => {
    if (!globalState.isLoggedIn) {
      return null;
    }

    // force refresh
    dataVersion.value;

    return await api.getInfo();
  }, null);

  ///////////////////////////////////////////////////////////
  // Functionality for interaction with backend side settings
  ///////////////////////////////////////////////////////////

  const userSettings = computedAsync(async () => {
    if (!globalState.isLoggedIn) {
      // TODO: return default settings?
      //       but how to form them?
      return null;
    }

    // force refresh
    dataVersion.value;

    return await api.getUserSettings();
  }, null);

  const userSettingsPresent = computed(() => {
    return userSettings.value !== null && userSettings.value !== undefined;
  });

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

  ///////////////////////
  // News filter settings
  ///////////////////////

  const lastEntriesPeriod = backendSettings(
    "view_news_filter_interval",
    (rawValue) => { return _.findKey(e.LastEntriesPeriod, (value) => value === rawValue); },
    e.LastEntriesPeriod.Day3
  );

  const entriesOrder = backendSettings(
    "view_news_filter_sort_by",
    (rawValue) => { return _.findKey(e.EntriesOrder, (value) => value === rawValue); },
    e.EntriesOrder.Score
  );

  const minTagCount = backendSettings(
    "view_news_filter_min_tags_count",
    (rawValue) => { return _.findKey(e.MinNewsTagCount, (value) => value === rawValue); },
    e.MinNewsTagCount.Two
  );

  const entriesOrderProperties = computed(() => {
    return e.EntriesOrderProperties.get(entriesOrder.value);
  });

  const showRead = backendSettings(
        "view_news_filter_show_read",
        (rawValue) => { return typeof rawValue === "boolean"; },
        true
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
    userSettingsPresent,
    info,
    feedsOrder,
    failedFeedsFirst,
    rulesOrder,
    showSidebar,
    showSidebarPoint
  };
});
