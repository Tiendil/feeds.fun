<template>
<div>
  <p> Try to subscribe for the feeds collections that we are preparing for you! </p>

  <ul class="mb-1">
    <li v-for="item in collections">
      <input
        class="ffun-checkbox"
        type="checkbox"
        :id="item"
        :name="item"
        :value="item"
        v-model="selectedCollections"
        checked />
      <label class="ml-2"
             :for="item">{{ item }}</label>
    </li>
  </ul>

  <button @click="subscribe()"
          class="ffun-form-button">Subscribe</button>
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
