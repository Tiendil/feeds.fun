<template>
  <div>

    <h3>
      <favicon-element
        :url="feed.url"
        class="w-5 h-5 mx-1 mb-1 inline align-middle" />

      <external-url
        class="ffun-normal-link"
        :url="feed.url"
        :text="feed.title"/>

    </h3>

    <p v-html="feed.description" />

    <ul class="list-disc list-inside">
      <li
        v-for="entry in feed.entries"
        :key="entry.url">

        <external-url
          class="ffun-normal-link"
          :url="entry.url"
          :text="entry.title"/>
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
