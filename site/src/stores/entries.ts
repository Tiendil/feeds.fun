import {computed, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";
import _ from "lodash";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import {Timer} from "@/logic/timer";
import {computedAsync} from "@vueuse/core";
import {useGlobalSettingsStore} from "@/stores/globalSettings";
import * as events from "@/logic/events";
import {useGlobalState} from "@/stores/globalState";


enum Mode {
  News = "news",
  PublicCollection = "public-collection",
}

export const useEntriesStore = defineStore("entriesStore", () => {
  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();

  const entries = ref<{[key: t.EntryId]: t.Entry}>({});
  const requestedEntries = ref<{[key: t.EntryId]: boolean}>({});
  const displayedEntryId = ref<t.EntryId | null>(null);
  const readHistory = ref<t.EntryId[]>([]);

  const canUndoMarkRead = computed(() => readHistory.value.length > 0);

  const mode = ref<Mode|null>(null);
  const modePublicCollectionSlug = ref<t.CollectionSlug|null>(null);

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

  function registerEntry(entry: t.Entry) {
    if (entry.id in entries.value) {
      if (entry.body === null && entries.value[entry.id].body !== null) {
        entry.body = entries.value[entry.id].body;
      }
    }

    entries.value[entry.id] = entry;
  }

  async function loadEntriesAccordingToMode() {
    const periodProperties = e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod);

    if (periodProperties === undefined) {
      throw new Error(`Unknown period ${globalSettings.lastEntriesPeriod}`);
    }

    const period = periodProperties.seconds;

    if (mode.value === Mode.News) {
      return await api.getLastEntries({
        period: period
      });
    }

    if (mode.value === Mode.PublicCollection) {
      return await api.getLastCollectionEntries({
        period: period,
        collectionSlug: modePublicCollectionSlug.value
      });
    }
  }

  const loadedEntriesReport = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;

    if (mode.value === null) {
      // Do nothing until the mode is set
      return [];
    }

    const loadedEntries = await loadEntriesAccordingToMode();

    const report = [];

    for (const entry of loadedEntries) {
      registerEntry(entry);
      report.push(entry.id);
    }

    return report;
  }, null);

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

    const entries = await api.getEntriesByIds({ids: ids});

    for (const entry of entries) {
      registerEntry(entry);
    }

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
    if (globalState.isLoggedIn) {
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
    if (globalState.isLoggedIn) {
      await api.removeMarker({entryId: entryId, marker: marker});
    }
  }

  async function displayEntry({entryId}: {entryId: t.EntryId}) {
    displayedEntryId.value = entryId;

    requestFullEntry({entryId: entryId});

    if (!entries.value[entryId].hasMarker(e.Marker.Read)) {
      await setMarker({
        entryId: entryId,
        marker: e.Marker.Read
      });
    }

    await events.newsBodyOpened({entryId: entryId});
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
  };
});
