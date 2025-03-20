<template>
  <public-side-panel-layout>
    <template #side-menu-item-1>
      For
      <config-selector
        :values="e.LastEntriesPeriodProperties"
        v-model:property="globalSettings.lastEntriesPeriod" />
    </template>

    <template #side-footer>
      <tags-filter
        :tags="tagsCount"
        :show-create-rule="true"
        change-source="news_tags_filter" />
    </template>

    <template #main-header>
      News
      <span v-if="entriesNumber > 0">[{{ entriesNumber }}]</span>
    </template>

    <template #main-footer> </template>

    <entries-list
      :entriesIds="entriesReport"
      :time-field="orderProperties.timeField"
      :tags-count="tagsCount"
      :showFromStart="25"
      :showPerPage="25" />
  </public-side-panel-layout>
</template>

<script lang="ts" setup>
  // TODO: unify code with NewsView.vue, move into a separate module
  import {computed, ref, onUnmounted, watch, provide} from "vue";
import { useRoute } from 'vue-router'
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as tagsFilterState from "@/logic/tagsFilterState";
  import * as e from "@/logic/enums";
  import type * as t from "@/logic/types";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useEntriesStore} from "@/stores/entries";
import _ from "lodash";


const route = useRoute();

  const globalSettings = useGlobalSettingsStore();
  const entriesStore = useEntriesStore();

  entriesStore.setPublicCollectionMode(route.params.collectionSlug);

  const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

  provide("tagsStates", tagsStates);

  globalSettings.updateDataVersion();

const entriesWithOpenedBody = ref<{[key: t.EntryId]: boolean}>({});

const orderProperties = e.EntriesOrderProperties.get(e.EntriesOrder.Published);

  const _sortedEntries = computed(() => {
    if (entriesStore.loadedEntriesReport === null) {
      return [];
    }

    // const orderProperties = e.EntriesOrderProperties.get(globalSettings.entriesOrder);

    // if (orderProperties === undefined) {
    //   throw new Error(`Unknown order ${globalSettings.entriesOrder}`);
    // }

    const field = orderProperties.orderField;
    const direction = orderProperties.direction;

    // let report = entriesStore.loadedEntriesReport.slice();

    // Pre-map to avoid repeated lookups in the comparator
    const mapped = entriesStore.loadedEntriesReport.map((entryId) => {
      // @ts-ignore
      return {entryId, value: entriesStore.entries[entryId][field]};
    });

    mapped.sort((a: {entryId: t.EntryId; value: any}, b: {entryId: t.EntryId; value: any}) => {
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

    const report = mapped.map((x) => x.entryId);

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

</script>

<style></style>
