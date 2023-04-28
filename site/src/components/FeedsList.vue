<template>
<div>
  <template v-if="feeds === null || sortedFeeds.length == 0">
    <p>No feeds</p>
  </template>

  <template v-else>

    <ul style="list-style-type: none; margin: 0; padding: 0;">
      <li v-for="feed in sortedFeeds"
          :key="feed.id"
          style="margin-bottom: 0.25rem;">
        <feed-for-list :feed="feed"/>
      </li>
    </ul>

  </template>
</div>

</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import * as t from "@/logic/types";

const properties = defineProps<{ feeds: Array[t.Feed]}>();

const sortedFeeds = computed(() => {
    return properties.feeds.sort((a, b) => {
        if (a.title < b.title) return -1;
        if (a.title > b.title) return 1;
        return 0;
    });
});

</script>

<style scoped>
</style>
