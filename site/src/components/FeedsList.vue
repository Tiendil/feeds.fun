<template>
  <div>
    <template v-if="feeds === null || feeds.length == 0">
      <p>No feeds</p>
    </template>

    <template v-else>
      <ul style="list-style-type: none; margin: 0; padding: 0">
        <li
          v-for="feed in feeds"
          :key="feed.id"
          style="margin-bottom: 0.25rem">
          <feed-for-list :feed="feed" />
        </li>
      </ul>
    </template>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import * as t from "@/logic/types";

  const properties = defineProps<{feeds: Array[t.Feed]}>();
</script>

<style scoped></style>
