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

    <collections-public-intro
      v-if="collection && !globalState.isLoggedIn"
      :collectionId="collection.id"
      :tag1Uid="medianTag1"
      :tag1Count="tagsCount[medianTag1] || 0"
      :tag2Uid="medianTag2"
      :tag2Count="tagsCount[medianTag2] || 0" />

  <div v-if="collection && globalState.isLoggedIn" class="ffun-info-good">
    <p>Welcome to curated <strong>{{collection.name}}</strong> news collection!</p>

    <p>Collection news are always shown in the order of publication.</p>
  </div>

    <entries-list
      :loading="entriesStore.loading"
      :entriesIds="entriesReport"
      :time-field="globalSettings.entriesOrderProperties.timeField"
      :tags-count="tagsCount"
      :show-score="false"
      :showFromStart="25"
      :showPerPage="25" />

</side-panel-layout>
</template>

<script lang="ts" setup>
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

globalSettings.entriesOrder = e.EntriesOrder.Published;

const entriesReport = computed(() => {
  let report = entriesStore.visibleEntries.slice();

  report = tagsStates.value.filterByTags(report, (entryId) => entriesStore.entries[entryId].tags);
  return report;
});

const tagsCount = computed(() => {
  const entriesToProcess = entriesReport.value.map((entryId) => entriesStore.entries[entryId]);

  return utils.countTags(entriesToProcess);
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

  const counts = utils.countTags(entriesToProcess);

  return utils.chooseTagByUsage({tagsCount: counts,
                                 border: 0.5 * entriesNumber,
                                 exclude: [medianTag1.value]});
});


</script>

<style></style>
