<template>
  <div>
    <h3>
      <a
        :href="feed.url"
        target="_blank"
        rel="noopener noreferrer">
        {{ feed.title }}
      </a>
    </h3>

    <p v-html="feed.description" />

    <ul>
      <li
        v-for="entry in feed.entries"
        :key="entry.url">
        <entry-info :entry="entry" />
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";

  const props = defineProps<{feed: t.FeedInfo}>();
</script>

<style scoped></style>
