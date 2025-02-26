<template>
  <div class="flex text-lg">
    <div class="ffun-body-list-icon-column">
      <a
        v-if="subscribed"
        href="#"
        @click.prevent="feedsStore.unsubscribe(feed.id)"
        title="Unsubscribe from this feed"
        class="text-red-500 hover:text-red-600 ti ti-x" />

      <a
        v-else
        href="#"
        @click.prevent="feedsStore.subscribe(feed.url)"
        title="Subscribe to this feed"
        class="text-green-600 hover:text-green-700 ti ti-plus" />
    </div>

    <body-list-favicon-column :url="feed.url" />

    <div class="flex-grow">
      <external-url
        class="ffun-normal-link"
        :url="feed.url"
        :text="purifiedTitle" />
    </div>
  </div>

  <body-list-entry-body
    class="ml-8"
    :url="null"
    :title="null"
    :loading="false"
    :text="purifiedDescription" />
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import * as utils from "@/logic/utils";
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

  const purifiedTitle = computed(() => {
    return utils.purifyTitle({raw: properties.feed.title, default_: properties.feed.url});
  });

  const purifiedDescription = computed(() => {
    return utils.purifyBody({raw: properties.feed.description, default_: "No description"});
  });
</script>

<style scoped></style>
