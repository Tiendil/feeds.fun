<template>
  <div
    ref="entryTop"
    class="flex text-lg">
    <div class="ffun-body-list-icon-column w-4">
      <app-tooltip :text="isRead ? 'Mark as unread' : 'Mark as read'">
        <button
          type="button"
          :aria-label="isRead ? 'Mark as unread' : 'Mark as read'"
          class="flex h-7 w-4 cursor-pointer items-center justify-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          @click="toggleReadState">
          <span
            aria-hidden="true"
            :class="[
              'block h-3 w-3 rounded-full border-2',
              isRead ? 'border-green-700' : 'border-orange-700 bg-orange-700'
            ]" />
        </button>
      </app-tooltip>
    </div>

    <div
      v-if="showScore"
      class="flex-shrink-0 w-8 text-center pr-1">
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
        @click="onTitleClick"
        v-html="purifiedTitle" />

      <entry-tags-list
        class="mt-0 pt-0"
        :tags="entry.tags"
        :tags-count="tagsCount"
        :show-all="showBody"
        @request-to-show-all="entriesStore.displayEntry({entryId: entry.id, view: eventsView})"
        :contributions="showScore ? entry.scoreContributions : {}" />
    </div>

    <app-tooltip placement="top-end">
      <body-list-reverse-time-column :time="entry.effectivePublishedAt" />

      <template #content>
        <div><span class="font-medium">Considered published at:</span> {{ formatDate(entry.effectivePublishedAt) }}</div>
        <div><span class="font-medium">First seen by Feeds Fun:</span> {{ formatDate(entry.firstSeenAt) }}</div>
        <div><span class="font-medium">Published by the source:</span> {{ formatDate(entry.sourcePublishedAt) }}</div>
      </template>
    </app-tooltip>
  </div>

  <body-list-entry-body
    v-if="showBody"
    class="justify-center"
    :url="entry.url"
    :title="purifiedTitle"
    :loading="entry.body === null"
    :text="purifiedBody"
    :references="references"
    @body-title-clicked="newsLinkOpenedEvent" />
</template>

<script lang="ts" setup>
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

  function formatDate(date: Date): string {
    return date.toLocaleString();
  }

  const purifiedTitle = computed(() => {
    return utils.purifyTitle({raw: entry.value.title, default_: "No title"});
  });

  const purifiedBody = computed(() => {
    return utils.purifyBody({raw: entry.value.body, default_: "No description"});
  });

  const references = computed(() => {
    const references = (entry.value.references ?? []).slice();

    references.sort((left, right) => {
      const leftProperties = e.ReferenceKindProperties.get(left.kind);
      const rightProperties = e.ReferenceKindProperties.get(right.kind);

      if (leftProperties === undefined) {
        throw new Error(`Unknown reference kind: ${left.kind}`);
      }

      if (rightProperties === undefined) {
        throw new Error(`Unknown reference kind: ${right.kind}`);
      }

      return leftProperties.priority - rightProperties.priority;
    });

    return references;
  });

  function newsLinkOpenedEvent() {
    asserts.defined(eventsView);
    events.newsLinkOpened({entryId: entry.value.id, view: eventsView});
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
      newsLinkOpenedEvent();
    }
  }

  onMounted(() => {
    entriesStore.requestFullEntry({entryId: properties.entryId});
  });

  async function toggleReadState() {
    if (isRead.value) {
      await entriesStore.removeMarker({
        entryId: properties.entryId,
        marker: e.Marker.Read
      });
    } else {
      await entriesStore.setMarker({
        entryId: properties.entryId,
        marker: e.Marker.Read
      });
    }
  }
</script>
