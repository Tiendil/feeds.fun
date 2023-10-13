<template>
  <div class="flex container">
    <div class="flex-shrink-0 w-8 text-right pr-1">
      <value-score
        :value="entry.score"
        :entry-id="entry.id"/>
    </div>

    <div class="flex-grow">
      <input-marker
        class="w-7"
        :marker="e.Marker.Read"
        :entry-id="entryId"
        on-text="read"
        off-text="new!" />

      <a
        href="#"
        class="text-decoration-none ml-1"
        v-if="!showBody"
        @click.prevent="displayBody()"
        >&#9660;</a
      >
      <a
        href="#"
        class="text-decoration-none ml-1"
        v-if="showBody"
        @click.prevent="showBody = false"
        >&#9650;</a
      >

      <favicon-element
        :url="entry.url"
        class="w-4 h-4 align-text-bottom mx-1 inline" />

      <a
        :href="entry.url"
        target="_blank"
        @click="onTitleClick()"
        rel="noopener noreferrer">
        {{ purifiedTitle }}
      </a>

      <template v-if="showTags">
        <br />
        <tags-list
          :tags="entry.tags"
          :tags-count="tagsCount"
          :contributions="entry.scoreContributions" />
      </template>

      <div
        v-if="showBody"
        class="flex justify-center">
        <div class="max-w-4xl">
          <h2>{{ purifiedTitle }}</h2>
          <p v-if="entry.body === null">loading...</p>
          <div
            v-if="entry.body !== null"
            v-html="purifiedBody" />
        </div>
      </div>
    </div>

    <div class="flex-shrink-0 w-4 pl-1">
      <value-date-time
        :value="timeFor"
        :reversed="true" />
    </div>
  </div>
</template>

<script lang="ts" setup>
  import _ from "lodash";
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";

  const entriesStore = useEntriesStore();

  const properties = defineProps<{
    entryId: t.EntryId;
    timeField: string;
    showTags: boolean;
    tagsCount: {[key: string]: number};
  }>();

  const entry = computed(() => {
    if (properties.entryId in entriesStore.entries) {
      return entriesStore.entries[properties.entryId];
    }

    throw new Error(`Unknown entry: ${properties.entryId}`);
  });

  const showBody = ref(false);

  const timeFor = computed(() => {
    if (entry.value === null) {
      return null;
    }

    return _.get(entry.value, properties.timeField, null);
  });

  function displayBody() {
    showBody.value = true;

    if (entry.value === null) {
      throw new Error("entry is null");
    }

    entriesStore.requestFullEntry({entryId: entry.value.id});
  }

  const purifiedTitle = computed(() => {
    if (entry.value === null) {
      return "";
    }

    // TODO: remove emojis?
    let title = DOMPurify.sanitize(entry.value.title, {ALLOWED_TAGS: []});

    if (title.length === 0) {
      title = "No title";
    }

    return title;
  });

  const purifiedBody = computed(() => {
    if (entry.value === null) {
      return "";
    }

    if (entry.value.body === null) {
      return "";
    }
    return DOMPurify.sanitize(entry.value.body);
  });

  async function onTitleClick() {
    await entriesStore.setMarker({
      entryId: properties.entryId,
      marker: e.Marker.Read
    });
  }
</script>

<style scoped>

/* TODO: replace to press? */
  .container :deep(img) {
    @apply max-w-full;
    @apply h-auto;
  }
</style>
