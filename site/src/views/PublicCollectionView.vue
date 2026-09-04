<template>
  <side-panel-layout
    :reloadButton="false"
    :login-required="false"
    :home-button="true">
    <template #side-menu-item-1>
      <collections-public-selector
        class="min-w-full"
        v-if="collection"
        :collection-id="collection.id" />
    </template>
    <template #side-menu-item-2>
      For
      <config-selector
        :values="e.LastEntriesPeriodProperties"
        v-model:property="globalSettings.lastEntriesPeriod" />
    </template>

    <template #side-menu-item-3>
      Sort by
      <span class="inline-flex items-center align-middle">
        <config-selector
          :values="e.EntriesOrderProperties"
          :property="e.EntriesOrder.Published"
          disabled />

        <ui-info-icon
          class="ml-1"
          text="Collections are always ordered by publication date."
          size="large" />
      </span>
    </template>

    <template #side-menu-item-4>
      Show tags
      <config-selector
        :values="e.MinNewsTagCountProperties"
        v-model:property="globalSettings.minTagCount" />
    </template>

    <template #side-menu-item-5>
      Show read

      <config-flag
        style="min-width: 2.5rem"
        v-model:flag="globalSettings.showRead"
        on-text="yes"
        off-text="no" />
    </template>

    <template #side-footer>
      <tags-filter
        :tags="tagsCount"
        :show-create-rule="false"
        :show-registration-invitation="showRegistrationInvitation" />
    </template>

    <template #main-header>
      News
      <span v-if="entriesNumber > 0">[{{ entriesNumber }}]</span>
    </template>

    <template #main-footer> </template>

    <ui-toolbar class="mb-2">
      <template #left>
        <ui-button
          v-if="collection && globalState.loginConfirmed"
          variant="primary"
          size="compact"
          :disabled="subscriptionAction.loading || subscriptionAction.succeeded"
          @click="subscribe()">
          {{ subscriptionAction.succeeded ? "Subscribed" : "Subscribe" }}
        </ui-button>

        <toolbar-undo-mark-read />
      </template>

      <template #right>
        <product-tokens />
      </template>
    </ui-toolbar>

    <collections-subscribing-progress :status="subscriptionAction.status" />

    <!-- currently we have a "nuance" with tags user experience in this block -->
    <!-- The tags work as expected till the user selects their own tags from other places -->
    <!-- after that we can get a situation, when, after clicking on a tag in the block, there will be no news displayed -->
    <!-- because the user previously selected tags that have no common news with the tags in the block -->
    <!-- That effect is possible only if the user has already interacted with the ags filter => should not be a problem -->
    <collections-public-intro
      v-if="collection && !globalState.loginConfirmed"
      :collectionId="collection.id"
      :tag1Uid="medianTag1"
      :tag1Count="tagsCount[medianTag1] || 0"
      :tag2Uid="medianTag2"
      :tag2Count="tagsCount[medianTag2] || 0" />

    <ui-advisory
      v-if="collection && globalState.loginConfirmed"
      tone="positive">
      <h4 class="ui-positive-guidance-title">
        Welcome to curated <strong>{{ collection.name }}</strong> news collection!
      </h4>

      <p>{{ collection.description }}</p>
    </ui-advisory>

    <notifications-loaded-old-news
      :entries="entriesStore.loadedEntriesReport?.entryIds || []"
      :fallback-used="entriesStore.loadedEntriesReport?.fallbackUsed || false"
      :period="e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod as any)" />

    <entries-list
      :loading="entriesStore.loading"
      :entriesIds="entriesReport"
      :tags-count="tagsCount"
      :show-score="false"
      :showFromStart="25"
      :showPerPage="25" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, watch, provide} from "vue";
  import type {ComputedRef} from "vue";
  import {useRoute, useRouter} from "vue-router";
  import * as tagsFilterState from "@/logic/tagsFilterState";
  import * as e from "@/logic/enums";
  import * as utils from "@/logic/utils";
  import type * as t from "@/logic/types";
  import {useAsyncAction} from "@/logic/asyncAction";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useEntriesStore} from "@/stores/entries";
  import {useCollectionsStore} from "@/stores/collections";
  import {useGlobalState} from "@/stores/globalState";

  const route = useRoute();
  const router = useRouter();

  const globalState = useGlobalState();
  const globalSettings = useGlobalSettingsStore();
  const entriesStore = useEntriesStore();
  const collections = useCollectionsStore();

  const collectionSlug = computed(() => route.params.collectionSlug as t.CollectionSlug);

  const showRegistrationInvitation = computed(() => {
    return globalState.logoutConfirmed;
  });

  const collection = computed(() => {
    if (!collectionSlug.value) {
      return null;
    }

    const result = collections.getCollectionBySlug({slug: collectionSlug.value});

    if (Object.keys(collections.collections).length > 0 && !result) {
      // TODO: implement better behaviour for broken slugs
      router.push({name: "main"});
    }

    return result;
  });

  const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

  const subscriptionAction = useAsyncAction();

  globalSettings.mainPanelMode = e.MainPanelMode.PublicCollection;

  // Required to separate real collection change (and reset tags filter) from the collection initialization
  const lastDefinedCollectionId = ref<t.CollectionId | null>(null);

  watch(
    collection,
    () => {
      if (!collection.value) {
        return;
      }

      entriesStore.setPublicCollectionMode(collection.value.slug);

      if (lastDefinedCollectionId.value !== null && lastDefinedCollectionId.value !== collection.value.id) {
        tagsStates.value.clear();
        subscriptionAction.reset();
      }

      if (lastDefinedCollectionId.value !== collection.value.id) {
        lastDefinedCollectionId.value = collection.value.id;
      }
    },
    {immediate: true}
  );

  provide("tagsStates", tagsStates);
  provide("eventsViewName", "public_collections");

  tagsFilterState.setSyncingTagsWithRoute({
    tagsStates: tagsStates.value as unknown as tagsFilterState.Storage,
    route,
    router
  });

  globalSettings.updateDataVersion();

  async function subscribe() {
    if (!collection.value) {
      return;
    }

    const collectionId = collection.value.id;

    try {
      await subscriptionAction.run(() => collections.subscribe({collectionsIds: [collectionId]}));
    } catch (error) {
      console.error(error);
    }
  }

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

  const medianTag1: ComputedRef<string> = computed(() => {
    // do not change tag when the filter changed
    if (tagsStates.value.hasSelectedTags && medianTag1.value) {
      return medianTag1.value;
    }

    const entriesNumber = entriesReport.value.length;

    const result = utils.chooseTagByUsage({tagsCount: tagsCount.value, border: 0.5 * entriesNumber, exclude: []});

    if (result === null) {
      return "";
    }

    return result;
  });

  const medianTag2: ComputedRef<string> = computed(() => {
    // do not change tag when the filter changed
    if (tagsStates.value.hasSelectedTags && medianTag2.value) {
      return medianTag2.value;
    }

    const entriesToProcess = entriesReport.value
      .map((entryId) => entriesStore.entries[entryId])
      .filter((entry) => entry.tags.includes(medianTag1.value));

    const entriesNumber = entriesToProcess.length;

    const counts = utils.countTags(entriesToProcess);

    const result = utils.chooseTagByUsage({
      tagsCount: counts,
      border: 0.5 * entriesNumber,
      exclude: [medianTag1.value]
    });

    if (result === null) {
      return "";
    }

    return result;
  });
</script>

<style></style>
