<template>
  <feed-list-columns class="mb-1 border-b pb-1 text-xs text-gray-500">
    <template #checked>
      <span title="Last load: how long ago news was last loaded from the feed; color shows current feed status">
        Last load
      </span>
    </template>

    <template #added>
      <span title="Subscribed: how long ago you added this feed">Subscribed</span>
    </template>

    <template #rate>
      <span title="News/day: number of news loaded per day">News/day</span>
    </template>

    <template #favicon>
      <span title="Site icon" />
    </template>

    <template #main>Feed</template>
  </feed-list-columns>

  <ul>
    <li
      v-for="feed in feeds"
      :key="feed.id"
      class="ffun-body-list-entry">
      <feed-for-list :feed="feed" />
    </li>
  </ul>
</template>

<script lang="ts" setup>
  import type * as t from "@/logic/types";
  import FeedListColumns from "@/components/feed_list/Columns.vue";

  defineProps<{feeds: Array<t.Feed>}>();
</script>
