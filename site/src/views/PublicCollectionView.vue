<template>
<side-panel-layout :reloadButton="false" :login-required="false">
  <template #side-menu-item-1>
    <collections-public-selector class="min-w-full" v-if="collection" :collection-id="collection.id" />

    <p v-if="collection"  class="ffun-info-common my-2">{{collection.description}}</p>
  </template>
    <template #side-menu-item-2>
      For
      <config-selector
        :values="e.LastEntriesPeriodProperties"
        v-model:property="globalSettings.lastEntriesPeriod" />
    </template>

    <template #side-menu-item-3>
      Show read

      <config-flag
        style="min-width: 2.5rem"
        v-model:flag="globalSettings.showRead"
        on-text="no"
        off-text="yes" />

      <button
        class="ffun-form-button py-0 ml-1"
        title='Undo last "mark read" operation'
        :disabled="!entriesStore.canUndoMarkRead"
        @click="entriesStore.undoMarkRead()">
        ↶
      </button>
    </template>

    <template #side-footer>
      <tags-filter
        :tags="tagsCount"
        :show-create-rule="false"
        :show-registration-invitation="true"/>
    </template>

    <template #main-header>
      News
      <span v-if="entriesNumber > 0">[{{ entriesNumber }}]</span>
    </template>

    <template #main-footer> </template>

      <div class="inline-block max-w-xl min-w-xl ffun-info-good text-center mx-2">
        <supertokens-login />
      </div>

      <entries-list
        :entriesIds="entriesReport"
        :time-field="orderProperties.timeField"
        :tags-count="tagsCount"
        :showFromStart="25"
        :showPerPage="25" />

</side-panel-layout>
</template>

<script lang="ts" setup>
  // TODO: unify code with NewsView.vue, move into a separate module
  import {computed, ref, onUnmounted, watch, provide} from "vue";
import { useRoute, useRouter } from 'vue-router'
import {computedAsync} from "@vueuse/core";
import * as api from "@/logic/api";
import * as tagsFilterState from "@/logic/tagsFilterState";
import * as e from "@/logic/enums";
import type * as t from "@/logic/types";
import {useGlobalSettingsStore} from "@/stores/globalSettings";
import {useEntriesStore} from "@/stores/entries";
import {useCollectionsStore} from "@/stores/collections";
import _ from "lodash";
import * as asserts from "@/logic/asserts";

const route = useRoute();
const router = useRouter();

const globalSettings = useGlobalSettingsStore();
const entriesStore = useEntriesStore();
const collections = useCollectionsStore();

const collectionSlug = computed(() => route.params.collectionSlug as t.CollectionSlug);

const collection = computed(() => collections.getCollectionBySlug({slug: collectionSlug.value}));

const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

watch(collection, () => {
  if (!collection.value) {
    return;
  }

  entriesStore.setPublicCollectionMode(collection.value.slug);

  tagsStates.value.clear();
},
{immediate: true});

provide("tagsStates", tagsStates);
provide("eventsViewName", "public_collections");

tagsFilterState.setSyncingTagsWithRoute({tagsStates: tagsStates.value as unknown as tagsFilterState.Storage,
                                         route,
                                         router});

  globalSettings.updateDataVersion();

const entriesWithOpenedBody = ref<{[key: t.EntryId]: boolean}>({});

const orderProperties = e.EntriesOrderProperties.get(e.EntriesOrder.Published);

asserts.defined(orderProperties);

  const _sortedEntries = computed(() => {
    if (entriesStore.loadedEntriesReport === null) {
      return [];
    }

    // const orderProperties = e.EntriesOrderProperties.get(globalSettings.entriesOrder);

    // if (orderProperties === undefined) {
    //   throw new Error(`Unknown order ${globalSettings.entriesOrder}`);
    // }

    // asserts.defined(orderProperties);

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
