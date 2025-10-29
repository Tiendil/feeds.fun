import _ from "lodash";
import {ref, computed} from "vue";
import {defineStore} from "pinia";
import {computedAsync} from "@vueuse/core";
import {useGlobalState} from "@/stores/globalState";

import * as e from "@/logic/enums";
import * as t from "@/logic/types";
import * as api from "@/logic/api";

export const useGlobalSettingsStore = defineStore("globalSettings", () => {
  const globalState = useGlobalState();

  // General
  const mainPanelMode = ref(e.MainPanelMode.Entries);
  const dataVersion = ref(0);

  function updateDataVersion() {
    dataVersion.value++;
  }

  ///////////////////////////////////////////////////////////
  // Functionality for interaction with backend side settings
  ///////////////////////////////////////////////////////////

  const _userSettings = computedAsync(async () => {
    if (!globalState.loginConfirmed) {
      return null;
    }

    dataVersion.value;

    let settings = await api.getUserSettings();

    settingsOverrides.value = {};

    return settings;
  }, null);

  const userSettingsPresent = computed(() => {
    return _userSettings.value !== null && _userSettings.value !== undefined;
  });

  function userSettingInfo(kind: string) {
    return computed(() => {
      if (!_userSettings.value || !(kind in _userSettings.value)) {
        return null;
      }

      const setting = _userSettings.value[kind];

      let value = setting.value;

      if (kind in settingsOverrides.value) {
        value = settingsOverrides.value[kind];
      }

      return {
        kind: setting.kind,
        name: setting.name,
        type: setting.type,
        value: value
      } as t.UserSetting;
    });
  }

  function _backgroundSetUserSetting(kind: string, value: t.UserSettingsValue) {
    api.setUserSetting({kind: kind, value: value}).catch((error) => {
      console.error(`Error in API call setUserSetting for kind "${kind}":`, error);
    });
  }

  // This dict is used for two purposes:
  // - To store settings that anonymous user changes while using the site.
  // - To close fast reactive loop after calling backendSettings.set.
  //   Without this, setting a setting will cause weired and complex chain
  //   of (re)loading data from the backend.
  var settingsOverrides = ref<{[key in keyof any]: t.UserSettingsValue}>({});

  function setUserSettings(kind: string, newValue: t.UserSettingsValue) {
    settingsOverrides.value[kind] = newValue;

    if (globalState.loginConfirmed) {
      _backgroundSetUserSetting(kind, newValue);
    }

    if (_userSettings.value) {
      _userSettings.value[kind].value = newValue;
    }

    // We do not call updateDataVersion() here
    // Because it causes request of the user settings from the backen
    // which is not required
    // All reactive code should be triggered by changes in settingsOverrides
  }

  function backendSettings(kind: string, validator: any, defaultValue: t.UserSettingsValue) {
    return computed({
      get() {
        if (kind in settingsOverrides.value) {
          return settingsOverrides.value[kind];
        }

        if (!globalState.loginConfirmed) {
          return defaultValue;
        }

        if (!_userSettings.value) {
          return null;
        }

        const setting = _userSettings.value[kind];

        if (!validator(setting.value)) {
          _backgroundSetUserSetting(kind, defaultValue);
          return defaultValue;
        }

        return setting.value;
      },

      set(newValue) {
        if (newValue === null || newValue === undefined) {
          console.warn(`Setting "${kind}" is set to null or undefined. This is not allowed.`);
          return;
        }
        setUserSettings(kind, newValue);
      }
    });
  }

  function boolBackendSettings(kind: string, defaultValue: t.UserSettingsValue) {
    return backendSettings(
      kind,
      (rawValue: t.UserSettingsValue) => {
        return typeof rawValue === "boolean";
      },
      defaultValue
    );
  }

  function enumBackendSettings(kind: string, enumProperties: any) {
    const defaultEntry = _.find([...enumProperties], ([, prop]) => prop.default);

    if (!defaultEntry) {
      throw new Error(`No default entry found for enum "${kind}"`);
    }

    let defaultValue = defaultEntry[0];

    return backendSettings(
      kind,
      (rawValue: t.UserSettingsValue) => {
        return enumProperties.has(rawValue);
      },
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
    return e.EntriesOrderProperties.get(entriesOrder.value as any);
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

  ////////////////
  // User settings
  ////////////////

  const hide_message_about_setting_up_key = userSettingInfo("hide_message_about_setting_up_key");
  const hide_message_about_adding_collections = userSettingInfo("hide_message_about_adding_collections");
  const hide_message_check_your_feed_urls = userSettingInfo("hide_message_check_your_feed_urls");

  const openai_api_key = userSettingInfo("openai_api_key");
  const gemini_api_key = userSettingInfo("gemini_api_key");

  const max_tokens_cost_in_month = userSettingInfo("max_tokens_cost_in_month");
  const process_entries_not_older_than = userSettingInfo("process_entries_not_older_than");

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
    userSettingsPresent,
    feedsOrder,
    failedFeedsFirst,
    rulesOrder,
    showSidebar,
    showSidebarPoint,
    setUserSettings,

    hide_message_about_setting_up_key,
    hide_message_about_adding_collections,
    hide_message_check_your_feed_urls,

    openai_api_key,
    gemini_api_key,

    max_tokens_cost_in_month,
    process_entries_not_older_than
  };
});
