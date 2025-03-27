<template>
<side-panel-layout :reloadButton="false" :login-required="false" :home-button="true">
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

    <!-- TODO: add tags suggestion to other notifications -->
      <div v-if="collection && !globalState.isLoggedIn" class="inline-block ffun-info-good">
        <h4>Hi there!</h4>

        <p>
          Welcome to <strong>Feeds Fun</strong> and our curated <strong>{{collection.name}}</strong> news collection!
        </p>

        <p>
          <strong>Feeds Fun</strong> ranks news based on tags, so you always see what matters most. We offer public collections to showcase our tagging system in action. Hope you'll enjoy it!
        </p>

        <p v-if="medianTag1 && medianTag2">
          Try out the tag filters on the left, for example, filter news by tag
          <entry-tag
            v-if="medianTag1"
            :uid="medianTag1"
            css-modifier="neutral"
            :count="tagsCount[medianTag1] || 0" />

          or even by a more specific tag

          <entry-tag
            v-if="medianTag2"
            :uid="medianTag2"
            css-modifier="neutral"
            :count="tagsCount[medianTag2] || 0" />
        </p>

        <p>
          If you like the results, <a href="#" @click.prevent="router.push({name: 'main'})">register</a> to create your own scoring rules and automatically prioritize the news you’re most interested in.
        </p>

        <p>
          You can find more about scoring rules on the <a :href="router.resolve({name: 'main', params: {}}).href">main page</a>.
        </p>

        <p><strong>All news in this collection is always up-to-date and tagged.</strong>
        </p>

      </div>

      <entries-list
        :loading="entriesStore.loading"
        :entriesIds="entriesReport"
        :time-field="orderProperties.timeField"
        :tags-count="tagsCount"
        :show-score="false"
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
import * as utils from "@/logic/utils";
import type * as t from "@/logic/types";
import {useGlobalSettingsStore} from "@/stores/globalSettings";
import {useEntriesStore} from "@/stores/entries";
import {useCollectionsStore} from "@/stores/collections";
  import {useGlobalState} from "@/stores/globalState";
import _ from "lodash";
import * as asserts from "@/logic/asserts";

const route = useRoute();
const router = useRouter();

  const globalState = useGlobalState();
const globalSettings = useGlobalSettingsStore();
const entriesStore = useEntriesStore();
const collections = useCollectionsStore();

const collectionSlug = computed(() => route.params.collectionSlug as t.CollectionSlug);

const collection = computed(() => {
  if (!collectionSlug.value) {
    return null;
  }

  const result = collections.getCollectionBySlug({slug: collectionSlug.value})

  if (Object.keys(collections.collections).length > 0 && !result) {
    // TODO: implement better behaviour for broken slugs
    router.push({name: "main"});
  }

  return result;
});

const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

globalSettings.mainPanelMode = e.MainPanelMode.PublicCollection;

// Required to separate real collection change (and reset tags filter) from the collection initialization
const lastDefinedCollectionId = ref<t.CollectionId | null>(null);

watch(collection, () => {
  if (!collection.value) {
    return;
  }

  entriesStore.setPublicCollectionMode(collection.value.slug);

  if (lastDefinedCollectionId.value !== null && lastDefinedCollectionId.value !== collection.value.id) {
    tagsStates.value.clear();
  }

  if (lastDefinedCollectionId.value !== collection.value.id) {
    lastDefinedCollectionId.value = collection.value.id;
  }
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
  // Todo refactor in other views
  const entriesToProcess = entriesReport.value.map((entryId) => entriesStore.entries[entryId]);

  return utils.countTagsForEntries(entriesToProcess);
});

  const entriesNumber = computed(() => {
    return entriesReport.value.length;
  });

const medianTag1 = computed(() => {
  // do not change tag when the filter changed
  if (tagsStates.value.hasSelectedTags) {
    return medianTag1.value;
  }

  const entriesNumber = entriesReport.value.length;

  return utils.chooseTagByUsage({tagsCount: tagsCount.value,
                                 border: 0.5 * entriesNumber});
});

const medianTag2 = computed(() => {
  // do not change tag when the filter changed
  if (tagsStates.value.hasSelectedTags) {
    return medianTag2.value;
  }

  const entriesToProcess = entriesReport.value.map((entryId) => entriesStore.entries[entryId]).filter((entry) => entry.tags.includes(medianTag1.value));

  const entriesNumber = entriesToProcess.length;

  const counts = utils.countTagsForEntries(entriesToProcess);

  return utils.chooseTagByUsage({tagsCount: counts,
                                 border: 0.5 * entriesNumber,
                                 exclude: [medianTag1.value]});
});


</script>

<style></style>
