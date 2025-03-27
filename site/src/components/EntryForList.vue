<template>
  <div
    ref="entryTop"
    :class="['flex', 'text-lg', {'ml-8': isRead}]">
    <div class="ffun-body-list-icon-column">
      <a
        v-if="isRead"
        href="#"
        @click.prevent="markUnread()"
        title="Mark as unread"
        class="text-green-700 ti ti-chevrons-left" />

      <a
        v-else
        href="#"
        @click.prevent="markRead()"
        title="Mark as read"
        class="text-orange-700 ti ti-chevrons-right" />
    </div>

    <div v-if="showScore" class="flex-shrink-0 w-8 text-center pr-1">
      <value-score
        :value="entry.score"
        :entry-id="entry.id" />
    </div>

    <body-list-favicon-column :url="entry.url" />

    <div class="flex-grow">
      <a
        :href="entry.url"
        target="_blank"
        :class="[{'font-bold': !isRead}, 'flex-grow', 'min-w-fit', 'line-clamp-1', 'pr-4', 'mb-0']"
        @click="onTitleClick">
        {{ purifiedTitle }}
      </a>

      <entry-tags-list
        class="mt-0 pt-0"
        :tags="entry.tags"
        :tags-count="tagsCount"
        :show-all="showBody"
        @request-to-show-all="entriesStore.displayEntry({entryId: entry.id, view: eventsView})"
        :contributions="entry.scoreContributions" />
    </div>

    <body-list-reverse-time-column
      :title="timeForTooltip"
      :time="timeFor" />
  </div>

  <body-list-entry-body
    v-if="showBody"
    class="justify-center"
    :url="entry.url"
    :title="purifiedTitle"
    :loading="entry.body === null"
    :text="purifiedBody"
    @body-title-clicked="newsLinkOpenedEvent" />
</template>

<script lang="ts" setup>
  import _ from "lodash";
  import {computed, ref, useTemplateRef, onMounted, inject} from "vue";
  import type * as t from "@/logic/types";
  import * as events from "@/logic/events";
  import * as e from "@/logic/enums";
import * as utils from "@/logic/utils";
  import * as asserts from "@/logic/asserts";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";

const entriesStore = useEntriesStore();

const eventsView = inject<events.EventsViewName>("eventsViewName");

asserts.defined(eventsView);

  const topElement = useTemplateRef("entryTop");

  const properties = defineProps<{
    entryId: t.EntryId;
    timeField: string;
    tagsCount: {[key: string]: number};
    showScore: boolean;
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

  const timeForTooltip = computed(() => {
    if (entry.value === null) {
      return "";
    }

    if (properties.timeField === "publishedAt") {
      return "How long ago the news was published";
    }

    if (properties.timeField === "catalogedAt") {
      return "How long ago the news was collected";
    }

    return "";
  });

  const purifiedTitle = computed(() => {
    return utils.purifyTitle({raw: entry.value.title, default_: "No title"});
  });

  const purifiedBody = computed(() => {
    return utils.purifyBody({raw: entry.value.body, default_: "No description"});
  });

async function newsLinkOpenedEvent() {
  asserts.defined(eventsView);
    await events.newsLinkOpened({entryId: entry.value.id, view: eventsView});
  }

async function onTitleClick(event: MouseEvent) {
  asserts.defined(eventsView);

    if (!event.ctrlKey) {
      event.preventDefault();
      event.stopPropagation();

      if (showBody.value) {
        entriesStore.hideEntry({entryId: entry.value.id});
      } else {
        await entriesStore.displayEntry({entryId: entry.value.id, view: eventsView});

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

  async function markUnread() {
    await entriesStore.removeMarker({
      entryId: properties.entryId,
      marker: e.Marker.Read
    });
  }

  async function markRead() {
    await entriesStore.setMarker({
      entryId: properties.entryId,
      marker: e.Marker.Read
    });
  }
</script>
