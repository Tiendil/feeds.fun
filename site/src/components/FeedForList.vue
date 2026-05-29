<template>
  <div
    ref="feedTop"
    v-if="feed !== null">
    <feed-list-columns class="text-lg">
      <template #action>
        <a
          href="#"
          class="text-red-500 hover:text-red-600"
          title="Unsubscribe"
          @click.prevent="feedsStore.unsubscribe(feed.id)">
          <icon icon="x" />
        </a>
      </template>

      <template #checked>
        <span
          :class="checkedClass"
          :title="checkedTitle">
          {{ checkedText }}
        </span>
      </template>

      <template #added>
        <span title="Added: how long ago you added this feed">
          <value-date-time
            :value="feed.linkedAt"
            :reversed="true" />
        </span>
      </template>

      <template #rate>
        <span
          :class="entriesPerDayClass"
          :title="entriesPerDayTitle">
          {{ feed.entriesPerDay }}/day
        </span>
      </template>

      <template #favicon>
        <favicon-element
          :url="feed.url"
          class="w-5 h-5 mx-1 inline align-text-bottom" />
      </template>

      <template #main>
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
      </template>
    </feed-list-columns>
  </div>

  <body-list-entry-body
    v-if="showDescription"
    class="justify-center"
    :url="bodyTitleUrl"
    :title="purifiedTitle"
    :loading="feed.entriesLoadedDetails === null"
    :references="feedReferences"
    :text="purifiedDescription">
    <template
      v-if="feed.entriesLoadedDetails !== null"
      #body-prefix>
      <feed-entries-per-day-chart :entries-loaded-details="feed.entriesLoadedDetails" />
    </template>
  </body-list-entry-body>
</template>

<script lang="ts" setup>
  import {computed, useTemplateRef} from "vue";
  import * as e from "@/logic/enums";
  import * as t from "@/logic/types";
  import * as utils from "@/logic/utils";
  import {useFeedsStore} from "@/stores/feeds";
  import {useCollectionsStore} from "@/stores/collections";
  import FeedListColumns from "@/components/feed_list/Columns.vue";
  import FeedEntriesPerDayChart from "@/components/feed_list/FeedEntriesPerDayChart.vue";

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

  const checkedText = computed(() => {
    if (properties.feed.loadedAt === null) {
      return "?";
    }

    return utils.timeSince(properties.feed.loadedAt);
  });

  const checkedClass = computed(() => {
    if (properties.feed.loadedAt === null) {
      return "text-yellow-700";
    }

    if (properties.feed.isOk) {
      return "text-green-700";
    }

    return "text-red-700";
  });

  const checkedTitle = computed(() => {
    if (properties.feed.loadedAt === null) {
      const title = "Last load: unknown, the feed has no load timestamp.";

      if (properties.feed.isOk) {
        return `${title} Status: loaded, no recent feed errors.`;
      }

      return `${title} Status: feed is failing, ${properties.feed.lastError || "unknown error"}.`;
    }

    if (properties.feed.isOk) {
      return "Last load: how long ago news was last loaded from the feed. Status: loaded, no recent feed errors.";
    }

    return `Last load: how long ago news was last loaded from the feed. Status: feed is failing, ${properties.feed.lastError || "unknown error"}.`;
  });

  const entriesPerDayTitle = computed(() => {
    const title = "News/day: number of news loaded per day over the current statistics window.";

    if (!properties.feed.young) {
      return title;
    }

    return `${title} This feed is young, so statistics may be inaccurate.`;
  });

  const entriesPerDayClass = computed(() => {
    return {
      "text-yellow-700": properties.feed.young
    };
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
