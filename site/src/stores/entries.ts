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

export const useEntriesStore = defineStore("entriesStore", () => {
  const globalSettings = useGlobalSettingsStore();

  const entries = ref<{[key: t.EntryId]: t.Entry}>({});
  const requestedEntries = ref<{[key: t.EntryId]: boolean}>({});

  const firstTimeEntriesLoading = ref(true);

  function registerEntry(entry: t.Entry) {
    if (entry.id in entries.value) {
      if (entry.body === null && entries.value[entry.id].body !== null) {
        entry.body = entries.value[entry.id].body;
      }
    }

    entries.value[entry.id] = entry;
  }

  const loadedEntriesReport = computedAsync(async () => {
    const periodProperties = e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod);

    if (periodProperties === undefined) {
      throw new Error(`Unknown period ${globalSettings.lastEntriesPeriod}`);
    }

    const period = periodProperties.seconds;

    // force refresh
    globalSettings.dataVersion;

    const loadedEntries = await api.getLastEntries({
      period: period
    });

    const report = [];

    for (const entry of loadedEntries) {
      registerEntry(entry);
      report.push(entry.id);
    }

    firstTimeEntriesLoading.value = false;

    return report;
  }, []);

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
    await api.setMarker({entryId: entryId, marker: marker});

    if (entryId in entries.value) {
      entries.value[entryId].setMarker(marker);
    }
  }

  async function removeMarker({entryId, marker}: {entryId: t.EntryId; marker: e.Marker}) {
    await api.removeMarker({entryId: entryId, marker: marker});

    if (entryId in entries.value) {
      entries.value[entryId].removeMarker(marker);
    }
  }

  return {
    entries,
    requestFullEntry,
    setMarker,
    removeMarker,
    firstTimeEntriesLoading,
    loadedEntriesReport
  };
});
