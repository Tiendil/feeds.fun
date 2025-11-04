import {computed, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";
import _ from "lodash";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import * as utils from "@/logic/utils";
import {Timer} from "@/logic/timer";
import {computedAsync} from "@vueuse/core";
import {useGlobalSettingsStore} from "@/stores/globalSettings";
import * as events from "@/logic/events";
import {useGlobalState} from "@/stores/globalState";

enum Mode {
  News = "news",
  PublicCollection = "public-collection"
}

export const useEntriesStore = defineStore("entriesStore", () => {
  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();

  const entries = ref<{[key: t.EntryId]: t.Entry}>({});
  const requestedEntries = ref<{[key: t.EntryId]: boolean}>({});
  const displayedEntryId = ref<t.EntryId | null>(null);
  const readHistory = ref<t.EntryId[]>([]);

  const canUndoMarkRead = computed(() => readHistory.value.length > 0);

  const mode = ref<Mode | null>(null);
  const modePublicCollectionSlug = ref<t.CollectionSlug | null>(null);

  function setNewsMode() {
    if (mode.value == Mode.News) {
      return;
    }

    mode.value = Mode.News;

    globalSettings.updateDataVersion();
  }

  function setPublicCollectionMode(collectionSlug: t.CollectionSlug) {
    if (mode.value == Mode.PublicCollection && modePublicCollectionSlug.value === collectionSlug) {
      return;
    }

    mode.value = Mode.PublicCollection;
    modePublicCollectionSlug.value = collectionSlug;

    globalSettings.updateDataVersion();
  }

  const readyToLoadNews = computed(() => {
    return (globalSettings.userSettingsPresent || !globalState.loginConfirmed) && mode.value !== null;
  });

  // Public collections uses fixed sorting order
  // News uses dynamic sorting order and should keep it between switching views
  // So, if we set globalSettings.entriesOrderProperties in PublicCollection view
  // we'll break News view sorting and confuse users
  // => we hardcode specific order properties for PublicCollection mode
  const activeOrderProperties = computed(() => {
    if (!readyToLoadNews.value) {
      // We can not load or process entries until everything is ready
      // => Return most general order
      return e.EntriesOrderProperties.get(e.EntriesOrder.Published) as unknown as e.EntriesOrderProperty;
    }

    if (mode.value == Mode.News) {
      // use saved order mode for News view
      return globalSettings.entriesOrderProperties as unknown as e.EntriesOrderProperty;
    }

    if (mode.value == Mode.PublicCollection) {
      // use fixed Published order for Public Collection view
      return e.EntriesOrderProperties.get(e.EntriesOrder.Published) as unknown as e.EntriesOrderProperty;
    }

    console.error(`Unknown mode ${mode.value}`);

    return e.EntriesOrderProperties.get(e.EntriesOrder.Published) as unknown as e.EntriesOrderProperty;
  });

  // We bulk update entries to avoid performance degradation
  // on triggering multiple reactivity updates for each entry
  function registerEntries({newEntries, updateTags}: {newEntries: t.Entry[]; updateTags: boolean}) {
    let delta: {[key: t.EntryId]: t.Entry} = {};

    for (const entry of newEntries) {
      if (entry.id in entries.value) {
        let existingEntry = entries.value[entry.id];

        if (entry.body === null && existingEntry.body !== null) {
          entry.body = existingEntry.body;
        }

        if (!updateTags) {
          entry.tags = _.cloneDeep(existingEntry.tags);
        }
      }
      delta[entry.id] = entry;
    }

    if (_.isEmpty(delta)) {
      return;
    }

    entries.value = {...entries.value, ...delta};
  }

  async function loadEntriesAccordingToMode() {
    const periodProperties = e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod as any);

    if (periodProperties === undefined) {
      throw new Error(`Unknown period ${globalSettings.lastEntriesPeriod}`);
    }

    const period = periodProperties.seconds;

    const minTagCount = e.MinNewsTagCountProperties.get(globalSettings.minTagCount as any)?.count;

    if (minTagCount === undefined) {
      throw new Error(`Unknown min tag count ${globalSettings.minTagCount}`);
    }

    if (mode.value === Mode.News) {
      return await api.getLastEntries({
        period: period,
        minTagCount: minTagCount
      });
    }

    if (mode.value === Mode.PublicCollection) {
      return await api.getLastCollectionEntries({
        period: period,
        collectionSlug: modePublicCollectionSlug.value,
        minTagCount: minTagCount
      });
    }

    throw new Error(`Unknown mode ${mode.value}`);
  }

  const loadedEntriesReport = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;

    if (!readyToLoadNews.value) {
      return null;
    }

    const loadedEntries = await loadEntriesAccordingToMode();

    const report = [];

    registerEntries({
      newEntries: loadedEntries,
      updateTags: true
    });

    for (const entry of loadedEntries) {
      report.push(entry.id);
    }

    return report;
  }, null);

  const _sortedEntries = computed(() => {
    if (!readyToLoadNews.value) {
      return [];
    }

    if (loadedEntriesReport.value === null) {
      return [];
    }

    const field = activeOrderProperties.value.orderField;
    const direction = activeOrderProperties.value.direction;

    const report = utils.sortIdsList({ids: loadedEntriesReport.value, storage: entries.value, field, direction});

    return report;
  });

  const visibleEntries = computed(() => {
    let report = _sortedEntries.value.slice();

    if (!globalSettings.showRead) {
      report = report.filter((entryId) => {
        if (displayedEntryId.value == entryId) {
          // always show read entries with open body
          // otherwise, they will hide right after opening it
          return true;
        }
        return !entries.value[entryId].hasMarker(e.Marker.Read);
      });
    }

    return report;
  });

  function requestFullEntry({entryId}: {entryId: t.EntryId}) {
    if (entryId in entries.value && entries.value[entryId].body !== null) {
      return;
    }

    requestedEntries.value[entryId] = true;
  }

  async function loadFullEntries() {
    const ids: t.EntryId[] = Object.keys(requestedEntries.value).map((key) => t.toEntryId(key));

    if (ids.length === 0) {
      return;
    }

    // We do not request tags for full entries
    // Because we have no approach to control which tags to exclude because of minTagCount filter
    // This method loads an additional info for a subset of entries
    // => we have no clear tag statistics on the backend
    const loadedEntries = await api.getEntriesByIds({ids: ids});

    registerEntries({
      newEntries: loadedEntries,
      updateTags: false
    });

    requestedEntries.value = {};
  }

  const requestedEntriesTimer = new Timer(loadFullEntries, 1000);

  requestedEntriesTimer.start();

  async function setMarker({entryId, marker}: {entryId: t.EntryId; marker: e.Marker}) {
    if (marker === e.Marker.Read) {
      readHistory.value.push(entryId);
    }

    // This code must be before the actual API request
    // to guarantee smooth UI transition to the new state
    // otherwise the UI will be updated two times which leads to flickering
    if (entryId in entries.value) {
      entries.value[entryId].setMarker(marker);
    }

    // This method may be called from public access pages, like public collections
    // In such case user may be not logged in and we should not send API requests
    if (globalState.loginConfirmed) {
      await api.setMarker({entryId: entryId, marker: marker});
    }
  }

  async function removeMarker({entryId, marker}: {entryId: t.EntryId; marker: e.Marker}) {
    if (marker === e.Marker.Read) {
      _.pull(readHistory.value, entryId);

      hideEntry({entryId: entryId});
    }

    // This code must be before the actual API request, see comment above
    if (entryId in entries.value) {
      entries.value[entryId].removeMarker(marker);
    }

    // This method may be called from public access pages, like public collections
    // In such case user may be not logged in and we should not send API requests
    if (globalState.loginConfirmed) {
      await api.removeMarker({entryId: entryId, marker: marker});
    }
  }

  async function displayEntry({entryId, view}: {entryId: t.EntryId; view: events.EventsViewName}) {
    displayedEntryId.value = entryId;

    requestFullEntry({entryId: entryId});

    if (!entries.value[entryId].hasMarker(e.Marker.Read)) {
      await setMarker({
        entryId: entryId,
        marker: e.Marker.Read
      });
    }

    await events.newsBodyOpened({entryId: entryId, view: view});
  }

  function hideEntry({entryId}: {entryId: t.EntryId}) {
    if (displayedEntryId.value === entryId) {
      displayedEntryId.value = null;
    }
  }

  function undoMarkRead() {
    if (readHistory.value.length === 0) {
      return;
    }

    const entryId = readHistory.value.pop() as t.EntryId;

    removeMarker({entryId: entryId, marker: e.Marker.Read});
  }

  // TODO: Refactor for better loading tracking in the front code and in the GUI.
  //       Currently, this property is working only for the first load.
  //       => It should always be refactored to work correctly.
  // ATTENTION: check every usage of this property while refactoring
  const loading = computed(() => {
    return loadedEntriesReport.value === null;
  });

  return {
    entries,
    requestFullEntry,
    setMarker,
    removeMarker,
    loadedEntriesReport,
    displayedEntryId,
    displayEntry,
    hideEntry,
    undoMarkRead,
    canUndoMarkRead,
    setNewsMode,
    setPublicCollectionMode,
    loading,
    visibleEntries,
    activeOrderProperties
  };
});
