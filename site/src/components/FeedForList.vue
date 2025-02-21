<template>
  <div
    v-if="feed !== null"
    class="flex text-lg">
    <div class="flex-shrink-0 min-w-fit pr-2">
      <a
        href="#"
        class="ffun-normal-link"
        @click.prevent="feedsStore.unsubscribe(feed.id)">
        remove
      </a>
    </div>

    <body-list-reverse-time-column
      title="How long ago the feed was last checked for news"
      :time="feed.loadedAt" />

    <body-list-reverse-time-column
      title="How long ago the feed was added"
      :time="feed.linkedAt" />

    <div class="flex-shrink-0 w-8 pr-1 text-right cursor-default">
      <span
        v-if="feed.isOk"
        title="everything is ok"
        class="text-green-700 cursor-default"
        >ok</span
      >
      <span
        v-else
        :title="feed.lastError || 'unknown error'"
        class="text-red-700 cursor-default"
        >⚠</span
      >
    </div>

    <body-list-favicon-column :url="feed.url"/>

    <div class="flex-grow">
      <value-url
        class="ffun-normal-link"
        :value="feed.url"
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
    class="ml-64"
    :url="null"
    :title="null"
    :loading="false"
    :text="purifiedDescription"/>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useFeedsStore} from "@/stores/feeds";
  import {useCollectionsStore} from "@/stores/collections";

  const globalSettings = useGlobalSettingsStore();
  const feedsStore = useFeedsStore();
  const collections = useCollectionsStore();

  const properties = defineProps<{feed: t.Feed}>();

  const noDescription = "No description";

  const purifiedTitle = computed(() => {
    if (properties.feed.title === null) {
      return properties.feed.url;
    }

    let title = DOMPurify.sanitize(properties.feed.title, {ALLOWED_TAGS: []}).trim();

    if (title.length === 0) {
      return properties.feed.url;
    }

    return title;
  });

  const purifiedDescription = computed(() => {
    if (properties.feed.description === null) {
      return noDescription;
    }

    let description = DOMPurify.sanitize(properties.feed.description).trim();

    if (description.length === 0) {
      return noDescription;
    }

    return description;
  });
</script>
