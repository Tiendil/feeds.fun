<template>
  <div>
    <h3 class="m-0 text-lg font-semibold leading-snug text-slate-900">{{ collection.name }}</h3>
    <p class="mb-0 mt-1 text-sm leading-relaxed text-slate-600">{{ collection.description }}</p>

    <div
      v-if="showFeeds"
      class="mt-2">
      <ul
        v-for="feed in feeds"
        :key="feed.url"
        class="ffun-body-list-entry">
        <collections-feed-item :feed="feed" />
      </ul>
    </div>

    <div class="mt-2 flex flex-wrap items-center gap-2">
      <ui-button
        variant="tonal"
        @click.prevent="subscribe">
        <template v-if="collection.feedsNumber === 1"> Subscribe to 1 feed </template>

        <template v-else> Subscribe to {{ collection.feedsNumber }} feeds </template>
      </ui-button>

      <ui-button
        variant="secondary"
        v-if="!showFeeds"
        @click.prevent="show"
        >Show feeds</ui-button
      >

      <ui-button
        variant="secondary"
        v-if="showFeeds"
        @click.prevent="hide"
        >Hide feeds</ui-button
      >

      <a
        :href="router.resolve({name: 'public-collection', params: {collectionSlug: collection.slug}}).href"
        class="ffun-normal-link text-sm font-medium"
        >Read news in the collection</a
      >
    </div>

    <collections-subscribing-progress
      :loading="loading"
      :loaded="loaded"
      :error="error" />
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import {useRouter} from "vue-router";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";

  const router = useRouter();

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
