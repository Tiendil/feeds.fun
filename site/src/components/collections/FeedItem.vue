<template>
<div>
  <strong>{{feed.title}}</strong>

  <p>{{feed.description}}</p>
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
  feed: t.CollectionFeedInfo;
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

</script>

<style scoped></style>
