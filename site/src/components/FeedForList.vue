<template>
  <div
    ref="feedTop"
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

    <div
      :class="entriesPerDayClass"
      :title="entriesPerDayTitle">
      {{ feed.entriesPerDay }}
    </div>

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

    <div class="flex-grow min-w-0">
      <div
        class="flex min-w-0 cursor-pointer items-baseline gap-2"
        @click="onTitleClick">
        <span
          class="flex-shrink-0 min-w-fit line-clamp-1 mb-0"
          v-html="purifiedTitle" />

        <span
          v-if="purifiedDescriptionPreview"
          class="min-w-0 flex-1 truncate text-sm text-gray-600">
          {{ purifiedDescriptionPreview }}
        </span>
      </div>

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
    v-if="showDescription"
    class="justify-center"
    :url="bodyTitleUrl"
    :title="purifiedTitle"
    :loading="feed.entriesLoadedDetails === null"
    :references="feedReferences"
    :text="purifiedDescription" />
</template>

<script lang="ts" setup>
  import {computed, useTemplateRef} from "vue";
  import * as e from "@/logic/enums";
  import * as t from "@/logic/types";
  import * as utils from "@/logic/utils";
  import {useFeedsStore} from "@/stores/feeds";
  import {useCollectionsStore} from "@/stores/collections";

  const feedsStore = useFeedsStore();
  const collections = useCollectionsStore();
  const topElement = useTemplateRef("feedTop");

  const properties = defineProps<{feed: t.Feed}>();

  const showDescription = computed(() => {
    return properties.feed.id == feedsStore.displayedFeedId;
  });

  const purifiedTitle = computed(() => {
    return utils.purifyTitle({raw: properties.feed.title, default_: properties.feed.url});
  });

  const purifiedDescriptionPreview = computed(() => {
    if (properties.feed.description === null) {
      return "";
    }

    return utils.purifyTitle({raw: properties.feed.description, default_: ""});
  });

  const purifiedDescription = computed(() => {
    return utils.purifyBody({raw: properties.feed.description, default_: "No description"});
  });

  const bodyTitleUrl = computed(() => {
    return properties.feed.siteUrl ?? properties.feed.url;
  });

  const feedReferences = computed(() => {
    return [
      new t.Reference({
        kind: e.ReferenceKind.Page,
        url: properties.feed.url,
        title: "feed",
        mimeType: null,
        width: null,
        height: null,
        duration: null,
        size: null,
        extra: null
      })
    ];
  });

  const entriesPerDayTitle = computed(() => {
    const title = "Number of news loaded per day.";

    if (!properties.feed.young) {
      return title;
    }

    return `${title} This feed is young, so statistics may be inaccurate.`;
  });

  const entriesPerDayClass = computed(() => {
    return [
      "ffun-body-list-number-column",
      {
        "text-yellow-700": properties.feed.young
      }
    ];
  });

  function onTitleClick(event: MouseEvent) {
    if (!event.ctrlKey) {
      event.preventDefault();
      event.stopPropagation();

      if (showDescription.value) {
        feedsStore.hideFeed({feedId: properties.feed.id});
      } else {
        feedsStore.displayFeed({feedId: properties.feed.id});

        if (topElement.value) {
          const rect = topElement.value.getBoundingClientRect();

          const isVisible =
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth);

          if (!isVisible) {
            topElement.value.scrollIntoView({behavior: "instant"});
          }
        }
      }
    }
  }
</script>
