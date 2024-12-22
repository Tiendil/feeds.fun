<template>
  <side-panel-layout>
    <template #side-menu-item-1>
      For
      <config-selector
        :values="e.LastEntriesPeriodProperties"
        v-model:property="globalSettings.lastEntriesPeriod" />
    </template>

    <template #side-menu-item-2>
      Sort by
      <config-selector
        :values="e.EntriesOrderProperties"
        v-model:property="globalSettings.entriesOrder" />
    </template>

    <template #side-menu-item-3>
      Show read:
      <config-flag
        style="min-width: 2.5rem"
        v-model:flag="globalSettings.showRead"
        on-text="no"
        off-text="yes" />
    </template>

    <template #side-footer>
      <tags-filter
        :tags="tagsCount"
        :show-create-rule="true" />
    </template>

    <template #main-header>
      News
      <span v-if="entriesNumber > 0">[{{ entriesNumber }}]</span>
    </template>

    <template #main-footer> </template>

    <notifications
      v-if="entriesStore.loadedEntriesReport !== null"
      :create-rule-help="hasEntries && !hasRules"
      :api-key="true"
      :collections-notification_="!hasEntries"
      :collections-warning_="false" />

    <entries-list
      :entriesIds="entriesReport"
      :time-field="timeField"
      :tags-count="tagsCount"
      :showFromStart="25"
      :showPerPage="25"/>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as tagsFilterState from "@/logic/tagsFilterState";
  import * as e from "@/logic/enums";
  import type * as t from "@/logic/types";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useEntriesStore} from "@/stores/entries";
  import _ from "lodash";

  const globalSettings = useGlobalSettingsStore();
  const entriesStore = useEntriesStore();

  const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

  provide("tagsStates", tagsStates);

  globalSettings.mainPanelMode = e.MainPanelMode.Entries;

  globalSettings.updateDataVersion();

const entriesWithOpenedBody = ref<{[key: t.EntryId]: boolean}>({});

const _sortedEntries = computed(() => {

  if (entriesStore.loadedEntriesReport === null) {
      return [];
  }

  const orderProperties = e.EntriesOrderProperties.get(globalSettings.entriesOrder);

  if (orderProperties === undefined) {
    throw new Error(`Unknown order ${globalSettings.entriesOrder}`);
  }

  const field = orderProperties.orderField;
  const direction = orderProperties.direction;

  // let report = entriesStore.loadedEntriesReport.slice();

  // Pre-map to avoid repeated lookups in the comparator
  const mapped = entriesStore.loadedEntriesReport.map(entryId => {
    return { entryId, value: entriesStore.entries[entryId][field] };
  });

    mapped.sort((a: t.EntryId, b: t.EntryId) => {
      if (a.value === null && b.value === null) {
        return 0;
      }

      if (a.value === null) {
        return 1;
      }

      if (b.value === null) {
        return -1;
      }

      if (a.value < b.value) {
        return direction;
      }

      if (a.value > b.value) {
        return -direction;
      }

      return 0;
    });

  const report = mapped.map(x => x.entryId);

  return report;
});


const _visibleEntries = computed(() => {

    let report = _sortedEntries.value.slice();

    if (!globalSettings.showRead) {
      report = report.filter((entryId) => {
        if (entriesStore.displayedEntryId == entryId) {
          // always show read entries with open body
          // otherwise, they will hide right after opening it
          return true;
        }
        return !entriesStore.entries[entryId].hasMarker(e.Marker.Read);
      });
    }

  return report;

  });

const entriesReport = computed(() => {

    let report = _visibleEntries.value.slice();

  report = tagsStates.value.filterByTags(report, (entryId) => entriesStore.entries[entryId].tags);

    return report;
  });

const tagsCount = computed(() => {
    const tagsCount: {[key: string]: number} = {};

    for (const entryId of entriesReport.value) {
      const entry = entriesStore.entries[entryId];

      for (const tag of entry.tags) {
        if (tag in tagsCount) {
          tagsCount[tag] += 1;
        } else {
          tagsCount[tag] = 1;
        }
      }
    }

    return tagsCount;
  });

  const entriesNumber = computed(() => {
    return entriesReport.value.length;
  });

  const hasEntries = computed(() => {
    return entriesNumber.value > 0;
  });

  const hasRules = computed(() => {
    if (entriesStore.loadedEntriesReport === null) {
      return false;
    }

    // TODO: it is a heuristic (score could be 0 even with rules)
    //       must be refactored to something more stable
    for (const entryId of entriesStore.loadedEntriesReport) {
      if (entriesStore.entries[entryId].score != 0) {
        return true;
      }
    }
    return false;
  });

  const timeField = computed(() => {
    const orderProperties = e.EntriesOrderProperties.get(globalSettings.entriesOrder);

    if (orderProperties === undefined) {
      throw new Error(`Unknown entries order: ${globalSettings.entriesOrder}`);
    }

    return orderProperties.timeField;
  });

</script>

<style></style>
