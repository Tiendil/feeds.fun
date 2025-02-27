<template>
  <div>
    <form @submit.prevent="subscribe">
      <collections-block-item
        v-for="collectionId in collections.collectionsOrder"
        v-model="selectedCollections"
        :collectionId="collectionId"
        :selectedCollections="selectedCollections" />

      <button
        type="submit"
        class="ffun-form-button mt-4"
        >Subscribe</button
      >

      <button
        type="button"
        class="ffun-form-button ml-2"
        @click.prevent="router.push({name: e.MainPanelMode.Collections, params: {}})"
        >Explore Feeds Library
      </button>

      <user-setting-for-notification
        class="ml-2"
        kind="hide_message_about_adding_collections"
        button-text="Hide this message" />
    </form>

    <collections-subscribing-progress
      :loading="loading"
      :loaded="loaded"
      :error="error" />
  </div>
</template>

<script lang="ts" setup>
  import {useRouter, RouterLink, RouterView} from "vue-router";
  import {computed, ref, watch} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";

  const router = useRouter();

  const loading = ref(false);
  const loaded = ref(false);
  const error = ref(false);

  const globalSettings = useGlobalSettingsStore();

  const collections = useCollectionsStore();

  const selectedCollections = ref<t.CollectionId[]>([]);

  // fill selectedCollections in case collections are already loaded
  selectedCollections.value.push(...collections.collectionsOrder);

  // fill selectedCollections in case collections are not loaded yet
  watch(
    () => collections.collectionsOrder,
    (newOrder) => {
      selectedCollections.value.push(...newOrder);
    },
    {once: true}
  );

  async function subscribe() {
    loading.value = true;
    loaded.value = false;
    error.value = false;

    try {
      await api.subscribeToCollections({
        collectionsIds: selectedCollections.value
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
</script>

<style scoped></style>
