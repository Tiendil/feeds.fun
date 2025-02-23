<template>
  <div>
    <h3>{{ collection.name }}</h3>
    <p class="">{{ collection.description }}</p>

    <div v-if="showFeeds">
      <ul
        v-for="feed in feeds"
        :key="feed.url"
        class="ffun-body-list-entry">
        <collections-feed-item :feed="feed" />
      </ul>
    </div>

    <button
      @click.prevent="subscribe"
      class="ffun-form-button mr-2">
      <template v-if="collection.feedsNumber === 1"> Subscribe to 1 feed </template>

      <template v-else> Subscribe to {{ collection.feedsNumber }} feeds </template>
    </button>

    <button
      v-if="!showFeeds"
      @click.prevent="show"
      class="ffun-form-button"
      >Show feeds</button
    >

    <button
      v-if="showFeeds"
      @click.prevent="hide"
      class="ffun-form-button"
      >Hide feeds</button
    >

    <collections-subscribing-progress
      :loading="loading"
      :loaded="loaded"
      :error="error" />
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";

  const properties = defineProps<{
    collectionId: t.CollectionId;
  }>();

  const globalSettings = useGlobalSettingsStore();

  const collections = useCollectionsStore();

  const collection = computed(() => collections.collections[properties.collectionId]);

  const loading = ref(false);
  const loaded = ref(false);
  const error = ref(false);
  const showFeeds = ref(false);

  async function subscribe() {
    loading.value = true;
    loaded.value = false;
    error.value = false;

    try {
      await api.subscribeToCollections({
        collectionsIds: [properties.collectionId]
      });

      loading.value = false;
      loaded.value = true;
      error.value = false;
    } catch (e) {
      console.error(e);

      loading.value = false;
      loaded.value = false;
      error.value = true;
    }

    globalSettings.updateDataVersion();
  }

  function show() {
    showFeeds.value = true;
  }

  function hide() {
    showFeeds.value = false;
  }

  const feeds = computedAsync(
    async () => {
      return await collections.getFeeds({collectionId: properties.collectionId});
    },
    [],
    {lazy: true}
  );
</script>
