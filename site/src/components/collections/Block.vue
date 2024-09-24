<template>
<div>
    <form @submit.prevent="subscribe">
      <ul class="mb-1">
        <li v-for="collectionId in collections.collectionsOrder">
          <collections-block-item
            v-model="selectedCollections"
            :collectionId="collectionId"
            :selectedCollections="selectedCollections"/>
        </li>
      </ul>

      <button
        type="submit"
        class="ffun-form-button"
        >Subscribe</button
      >
    </form>

    <p
      v-if="loading"
      class="ffun-info-attention"
      >subscribing...</p
    >

    <p
      v-if="loaded"
      class="ffun-info-good"
      >Feeds added!</p
    >

    <p
      v-if="error"
      class="ffun-info-bad"
      >Unknown error occurred! Please, try later.</p
    >
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

const loading = ref(false);
const loaded = ref(false);
const error = ref(false);

const selectedCollections = ref<t.FeedsCollectionId[]>([]);

const globalSettings = useGlobalSettingsStore();

const collections = useCollectionsStore();

async function subscribe() {
  loading.value = true;
  loaded.value = false;
  error.value = false;

  try {
    await api.subscribeToFeedsCollections({
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
