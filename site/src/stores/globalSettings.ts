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

  var anonymousSettingsOverrides = ref({});

  function backendSettings(kind, validator, defaultValue) {
    return computed({
      get() {
        if (!globalState.isLoggedIn) {
          if (kind in anonymousSettingsOverrides.value) {
            return anonymousSettingsOverrides.value[kind];
          }
          return defaultValue;
        }

        if (!userSettings.value) {
          return null;
        }

        const setting = userSettings.value[kind];

        if (!validator(setting.value)) {
          backgroundSetUserSetting(kind, defaultValue);
          return defaultValue;
        }

        return setting.value;
      },

      async set(newValue) {

        if (!globalState.isLoggedIn) {
          anonymousSettingsOverrides.value[kind] = newValue;
          return;
        }

        userSettings.value[kind].value = newValue;
        backgroundSetUserSetting(kind, newValue);

        // TODO: do we need it here?
        updateDataVersion();
      }
    });

  }

  function boolBackendSettings(kind, defaultValue) {
    return backendSettings(
      kind,
      (rawValue) => { return typeof rawValue === "boolean"; },
      defaultValue
    );
  }

  function enumBackendSettings(kind, enumProperties) {
    const defaultEntry = _.find(
      [...enumProperties],
      ([, prop]) => prop.default
    );

    if (!defaultEntry) {
      throw new Error(`No default entry found for enum "${kind}"`);
    }

    let defaultValue = defaultEntry[0];

    return backendSettings(
      kind,
      (rawValue) => { return enumProperties.has(rawValue); },
      defaultValue
    );
  }

  ///////////////////////
  // News filter settings
  ///////////////////////

  const lastEntriesPeriod = enumBackendSettings("view_news_filter_interval", e.LastEntriesPeriodProperties);
  const entriesOrder = enumBackendSettings("view_news_filter_sort_by", e.EntriesOrderProperties);
  const minTagCount = enumBackendSettings("view_news_filter_min_tags_count", e.MinNewsTagCountProperties);
  const showRead = boolBackendSettings("view_news_filter_show_read", true);

  const entriesOrderProperties = computed(() => {
    return e.EntriesOrderProperties.get(entriesOrder.value);
  });

  ////////////////////////
  // Feeds filter settings
  ////////////////////////

  const showFeedsDescriptions = boolBackendSettings("view_feeds_show_feed_descriptions", true);
  const feedsOrder = enumBackendSettings("view_feeds_feed_order", e.FeedsOrderProperties);
  const failedFeedsFirst = boolBackendSettings("view_feeds_failed_feeds_first", false);

  ////////////////////////
  // Rules filter settings
  ////////////////////////

  const rulesOrder = enumBackendSettings("view_rules_order", e.RulesOrderProperties);

  ///////////////////
  // Sidebar settings
  ///////////////////

  const showSidebar = boolBackendSettings("show_sidebar", true);
  const showSidebarPoint = ref(false);

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
