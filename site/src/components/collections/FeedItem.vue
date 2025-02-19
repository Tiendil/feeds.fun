<template>
  <div class="flex">
    <div class="flex-shrink-0 w-20 text-right">
      <a
        href="#"
        v-if="!subscribed"
        @click.prevent.stop="feedsStore.subscribe(feed.url)"
        class="text-blue-700"
        >subscribe</a
      >

      <span
        v-else
        class="text-green-700 cursor-default"
        >subscribed</span
      >
    </div>

    <div class="flex-shrink-0 w-8 text-right pr-1">
      <favicon-element
        :url="feed.url"
        class="w-4 h-4 align-text-bottom mx-1 inline" />
    </div>

    <div class="flex-grow">
      <strong>{{ feed.title }}</strong>
    </div>
  </div>

  <div class="flex">
    <div class="flex-shrink-0 w-20 mr-1"> </div>

    <div class="max-w-3xl flex-1 bg-white border-2 rounded p-4">
      <p>{{ feed.description }}</p>
    </div>
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
  import {useFeedsStore} from "@/stores/feeds";

  const feedsStore = useFeedsStore();

  const properties = defineProps<{
    feed: t.CollectionFeedInfo;
  }>();

  const globalSettings = useGlobalSettingsStore();

  const subscribed = computed(() => properties.feed.id in feedsStore.feeds);
</script>

<style scoped></style>
