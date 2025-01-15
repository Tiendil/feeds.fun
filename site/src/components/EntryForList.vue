<template>
  <div
    ref="entryTop"
    class="flex text-lg">
    <div :class="['flex-shrink-0', 'text-right', {'ml-8': isRead}]">
      <input-marker
        class="w-7 mr-2"
        :marker="e.Marker.Read"
        :entry-id="entryId">
        <template v-slot:marked>
          <span
            class="text-green-700 no-underline"
            title="Mark as unread">
            <i class="ti ti-chevrons-left" />
          </span>
        </template>

        <template v-slot:unmarked>
          <span
            class="text-orange-700 no-underline"
            title="Mark as read">
            <i class="ti ti-chevrons-right" />
          </span>
        </template>
      </input-marker>
    </div>

    <div class="flex-shrink-0 w-8 text-center pr-1">
      <value-score
        :value="entry.score"
        :entry-id="entry.id" />
    </div>

    <div class="flex-shrink-0 w-8 text-right pr-1">
      <favicon-element
        :url="entry.url"
        class="w-5 h-5 align-text-bottom mx-1 inline" />
    </div>

    <div class="flex-grow">
      <a
        :href="entry.url"
        target="_blank"
        :class="[{'font-bold': !isRead}, 'flex-grow', 'min-w-fit', 'line-clamp-1', 'pr-4', 'mb-0']"
        @click="onTitleClick">
        {{ purifiedTitle }}
      </a>

      <tags-list
        class="mt-0 pt-0"
        :tags="entry.tags"
        :tags-count="tagsCount"
        :show-all="showBody"
        @request-to-show-all="entriesStore.displayEntry({entryId: entry.id})"
        :contributions="entry.scoreContributions" />
    </div>

    <div class="flex flex-shrink-0">
      <div class="w-7">
        <value-date-time
          :value="timeFor"
          :reversed="true" />
      </div>
    </div>
  </div>

  <div
    v-if="showBody"
    class="flex justify-center my-1">
    <div class="max-w-3xl flex-1 bg-slate-50 border-2 rounded p-4">
      <h2 class="mt-0"
        ><a
          :href="entry.url"
          target="_blank"
          @click="newsLinkOpenedEvent"
          >{{ purifiedTitle }}</a
        ></h2
      >
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
  import {computed, ref, useTemplateRef, onMounted} from "vue";
  import type * as t from "@/logic/types";
  import * as events from "@/logic/events";
  import * as e from "@/logic/enums";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";

  const entriesStore = useEntriesStore();

  const topElement = useTemplateRef("entryTop");

  const properties = defineProps<{
    entryId: t.EntryId;
    timeField: string;
    tagsCount: {[key: string]: number};
  }>();

  const entry = computed(() => {
    if (properties.entryId in entriesStore.entries) {
      return entriesStore.entries[properties.entryId];
    }

    throw new Error(`Unknown entry: ${properties.entryId}`);
  });

  const isRead = computed(() => {
    return entriesStore.entries[entry.value.id].hasMarker(e.Marker.Read);
  });

  const showBody = computed(() => {
    return entry.value.id == entriesStore.displayedEntryId;
  });

  const timeFor = computed(() => {
    if (entry.value === null) {
      return null;
    }

    return _.get(entry.value, properties.timeField, null);
  });

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

  async function newsLinkOpenedEvent() {
    await events.newsLinkOpened({entryId: entry.value.id});
  }

  async function onTitleClick(event: MouseEvent) {
    if (!event.ctrlKey) {
      event.preventDefault();
      event.stopPropagation();

      if (showBody.value) {
        entriesStore.hideEntry({entryId: entry.value.id});
      } else {
        await entriesStore.displayEntry({entryId: entry.value.id});

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
    } else {
      await newsLinkOpenedEvent();
    }
  }

  onMounted(() => {
    entriesStore.requestFullEntry({entryId: properties.entryId});
  });
</script>
