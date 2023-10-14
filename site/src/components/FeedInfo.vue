<template>
  <div>
    <h2>
      <a
        class="ffun-normal-link"
        :href="feed.url"
        target="_blank"
        rel="noopener noreferrer">
        {{ feed.title }}
      </a>
    </h2>

    <p v-html="feed.description" />

    <ul class="list-disc list-inside">
      <li
        v-for="entry in feed.entries"
        :key="entry.url">
        <a
          class="ffun-normal-link"
          :href="entry.url"
          target="_blank"
          rel="noopener noreferrer">
          {{ entry.title }}
        </a>
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import {useEntriesStore} from "@/stores/entries";

  const props = defineProps<{feed: t.FeedInfo}>();
</script>

<style scoped></style>
