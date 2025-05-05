<template>
  <div
    v-if="feed !== null"
    class="flex text-lg">
    <div class="ffun-body-list-icon-column">
      <a
        href="#"
        class="text-red-500 hover:text-red-600"
        title="Unsubscribe"
        @click.prevent="feedsStore.unsubscribe(feed.id)">
        <icon icon="x" />
      </a>
    </div>

    <body-list-reverse-time-column
      title="How long ago the feed was last checked for news"
      :time="feed.loadedAt" />

    <body-list-reverse-time-column
      title="How long ago the feed was added"
      :time="feed.linkedAt" />

    <div class="ffun-body-list-icon-column ml-3">
      <icon
        v-if="feed.isOk"
        title="everything is ok"
        icon="face-smile"
        class="text-green-700" />
      <icon
        v-else
        :title="feed.lastError || 'unknown error'"
        icon="face-sad"
        class="text-red-700" />
    </div>

    <body-list-favicon-column :url="feed.url" />

    <div class="flex-grow">
      <external-url
        class="ffun-normal-link"
        :url="feed.url"
        :text="purifiedTitle" />

      <template v-if="feed.collectionIds.length > 0">
        <span v-for="(collectionId, index) in feed.collectionIds">
          <template v-if="collectionId in collections.collections">
            <br />
            Collections:
            <span class="text-green-700 font-bold">{{ collections.collections[collectionId].name }}</span
            ><span v-if="index < feed.collectionIds.length - 1">, </span>
          </template>
        </span>
      </template>
    </div>
  </div>

  <body-list-entry-body
    v-if="globalSettings.showFeedsDescriptions"
    class="ml-56"
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
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useFeedsStore} from "@/stores/feeds";
  import {useCollectionsStore} from "@/stores/collections";

  const globalSettings = useGlobalSettingsStore();
  const feedsStore = useFeedsStore();
  const collections = useCollectionsStore();

  const properties = defineProps<{feed: t.Feed}>();

  const purifiedTitle = computed(() => {
    return utils.purifyTitle({raw: properties.feed.title, default_: properties.feed.url});
  });

  const purifiedDescription = computed(() => {
    return utils.purifyBody({raw: properties.feed.description, default_: "No description"});
  });
</script>
