<template>
<div class="flex container">

  <div class="flex-shrink-0 w-8 text-right pr-1">
    <value-score
      :value="entry.score"
      :entry-id="entry.id"/>
  </div>

  <div class="flex-shrink-0 w-8 text-right pr-1">
    <favicon-element
      :url="entry.url"
      class="w-4 h-4 align-text-bottom mx-1 inline" />
  </div>

  <div class="flex-grow">
    <a
      :href="entry.url"
      target="_blank"
      :class="[{'font-bold': isRead}, 'flex-grow', 'min-w-fit', 'line-clamp-1', 'pr-4', 'mb-0']"
      @click="onTitleClick">
      {{ purifiedTitle }}
    </a>

    <tags-list
      v-if="showTags"
      class="mt-0 pt-0"
      :tags="entry.tags"
      :tags-count="tagsCount"
      :contributions="entry.scoreContributions" />
  </div>

  <div class="flex flex-shrink-0">
    <input-marker
      class="w-7 mr-2"
      :marker="e.Marker.Read"
      :entry-id="entryId"
      on-text="read"
      off-text="new" />

    <div class="w-7">
      <value-date-time
        :value="timeFor"
        :reversed="true" />
    </div>
  </div>
</div>

<div
  v-if="showBody"
  class="flex justify-center mt-1">
  <div class="max-w-3xl flex-1 bg-slate-50 border-2 rounded p-4">
    <h2 class="mt-0"><a :href="entry.url" target="_blank">{{ purifiedTitle }}</a></h2>
    <p v-if="entry.body === null">loading...</p>
    <div
      v-if="entry.body !== null"
      class="prose max-w-none"
      v-html="purifiedBody" />
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

const isRead = computed(() => {
  return !entriesStore.entries[entry.value.id].hasMarker(e.Marker.Read)
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

function hideBody() {
  showBody.value = false;
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

async function onTitleClick(event) {


  if (!event.ctrlKey) {
    event.preventDefault();
    event.stopPropagation();

    if (showBody.value) {
      hideBody();
    }
    else {
      displayBody()
    }
  }

  // TODO: is it will be too slow?
  if (showBody.value) {
    await entriesStore.setMarker({
      entryId: properties.entryId,
      marker: e.Marker.Read
    });
  }

}
</script>

<style scoped>

/* TODO: replace to press? */
  .container :deep(img) {
    @apply max-w-full;
    @apply h-auto;
  }
</style>
