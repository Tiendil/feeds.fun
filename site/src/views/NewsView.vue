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
      <tags-filter :tags="tagsCount" :show-create-rule="true"/>
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
      :showPerPage="25"
      @entry:bodyVisibilityChanged="onBodyVisibilityChanged" />
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

// TODO: separate by 3 steps / computed attributes:
// 1. get slice
// 2. sort (because sort changing is less common)
// 3. filter
  const entriesReport = computed(() => {
    if (entriesStore.loadedEntriesReport === null) {
      return [];
    }

    let report = entriesStore.loadedEntriesReport.slice();

    if (!globalSettings.showRead) {
      report = report.filter((entryId) => {
        if (entriesWithOpenedBody.value[entryId]) {
          // always show read entries with open body
          // otherwise, they will hide right after opening it
          return true;
        }
        return !entriesStore.entries[entryId].hasMarker(e.Marker.Read);
      });
    }

    report = tagsStates.value.filterByTags(report, (entryId) => entriesStore.entries[entryId].tags);

    report = report.sort((a: t.EntryId, b: t.EntryId) => {
      const orderProperties = e.EntriesOrderProperties.get(globalSettings.entriesOrder);

      if (orderProperties === undefined) {
        throw new Error(`Unknown order ${globalSettings.entriesOrder}`);
      }

      const field = orderProperties.orderField;

      const valueA = _.get(entriesStore.entries[a], field, null);
      const valueB = _.get(entriesStore.entries[b], field, null);

      if (valueA === null && valueB === null) {
        return 0;
      }

      if (valueA === null) {
        return 1;
      }

      if (valueB === null) {
        return -1;
      }

      if (valueA < valueB) {
        return orderProperties.direction;
      }

      if (valueA > valueB) {
        return -orderProperties.direction;
      }

      return 0;
    });

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

// TODO: should we have only single entry with opened body?
//       in such case, remove this signal
  function onBodyVisibilityChanged({entryId, visible}: {entryId: t.EntryId; visible: boolean}) {
    entriesWithOpenedBody.value[entryId] = visible;
  }
</script>

<style></style>
