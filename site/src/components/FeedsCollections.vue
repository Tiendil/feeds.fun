<template>
  <div>
    <template v-for="item in collections">
      <input
        type="checkbox"
        :id="item"
        :name="item"
        :value="item"
        v-model="selectedCollections"
        checked />
      <label :for="item">{{ item }}</label>
      <br />
    </template>

    <br />

    <button @click="subscribe()">Subscribe</button>
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

  const selectedCollections = ref<t.FeedsCollectionId[]>([]);

  const globalSettings = useGlobalSettingsStore();

  const collections = computedAsync(async () => {
    const collections = await api.getFeedsCollections();

    for (const collectionId of collections) {
      selectedCollections.value.push(collectionId);
    }

    return collections;
  });

  async function subscribe() {
    await api.subscribeToFeedsCollections({
      collectionsIds: selectedCollections.value
    });
    globalSettings.updateDataVersion();
  }
</script>

<style scoped></style>
