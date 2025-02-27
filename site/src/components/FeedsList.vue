<template>
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
  import {computed, ref, onUnmounted, watch} from "vue";
  import type * as t from "@/logic/types";

  const properties = defineProps<{feeds: Array<t.Feed>}>();
</script>
