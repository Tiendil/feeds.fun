<template>
  <div>
    <form @submit.prevent="subscribe">
      <collections-block-item
        v-for="collectionId in collections.collectionsOrder"
        v-model="selectedCollections"
        :collectionId="collectionId"
        :selectedCollections="selectedCollections" />

      <ui-button
        variant="primary"
        type="submit"
        class="mt-4"
        >Subscribe</ui-button
      >

      <ui-button
        variant="secondary"
        type="button"
        class="ml-2"
        @click.prevent="router.push({name: e.MainPanelMode.Collections, params: {}})"
        >Explore Feeds Library
      </ui-button>

      <user-setting-for-notification
        class="ml-2"
        kind="hide_message_about_adding_collections"
        button-text="Hide this message" />
    </form>

    <collections-subscribing-progress :status="subscriptionAction.status" />
  </div>
</template>

<script lang="ts" setup>
  import {useRouter, RouterLink, RouterView} from "vue-router";
  import {computed, ref, watch} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";
  import {useCollectionsStore} from "@/stores/collections";
  import {useAsyncAction} from "@/logic/asyncAction";

  const router = useRouter();

  const subscriptionAction = useAsyncAction();

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
    try {
      await subscriptionAction.run(() =>
        collections.subscribe({
          collectionsIds: selectedCollections.value
        })
      );
    } catch (e) {
      console.error(e);
    }
  }
</script>

<style scoped></style>
