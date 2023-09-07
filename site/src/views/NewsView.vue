<template>
  <side-panel-layout>
    <template #side-menu-item-1>
      For the last
      <config-selector
        :values="e.LastEntriesPeriodProperties"
        v-model:property="globalSettings.lastEntriesPeriod" />
    </template>

    <template #side-menu-item-2>
      Sorted by
      <config-selector
        :values="e.EntriesOrderProperties"
        v-model:property="globalSettings.entriesOrder" />
    </template>

    <template #side-menu-item-3>
      Show tags:
      <config-flag
        v-model:flag="globalSettings.showEntriesTags"
        on-text="yes"
        off-text="no" />
    </template>

    <template #side-menu-item-4>
      Show already read:
      <config-flag
        v-model:flag="globalSettings.showRead"
        on-text="yes"
        off-text="no" />
    </template>

    <template #side-footer>
      <tags-filter
        :tags="tagsCount"
        @tag:stateChanged="onTagStateChanged" />
    </template>

    <template #main-header>
      News
      <span v-if="entriesNumber > 0">[{{ entriesNumber }}]</span>
    </template>

    <template #main-footer> </template>

    <template v-if="!hasEntries && !entriesStore.firstTimeEntriesLoading">
      <p>It looks like you have no news to read.</p>
      <p> Try to subscribe for the feeds collections that we are preparing for you! </p>
      <feeds-collections />
    </template>

    <entries-list
      :entriesIds="entriesReport"
      :time-field="timeField"
      :show-tags="globalSettings.showEntriesTags"
      :tags-count="tagsCount"
      :showFromStart="25"
      :showPerPage="25" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
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

  globalSettings.mainPanelMode = e.MainPanelMode.Entries;

  globalSettings.updateDataVersion();

  const entriesReport = computed(() => {
    let report = entriesStore.loadedEntriesReport.slice();

    if (!globalSettings.showRead) {
      report = report.filter((entryId) => {
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
        return 1;
      }

      if (valueA > valueB) {
        return -1;
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

  const timeField = computed(() => {
    const orderProperties = e.EntriesOrderProperties.get(globalSettings.entriesOrder);

    if (orderProperties === undefined) {
      throw new Error(`Unknown entries order: ${globalSettings.entriesOrder}`);
    }

    return orderProperties.timeField;
  });

  function onTagStateChanged({tag, state}: {tag: string; state: tagsFilterState.State}) {
    tagsStates.value.onTagStateChanged({tag, state});
  }
</script>

<style></style>
