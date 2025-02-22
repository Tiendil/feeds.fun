<template>
  <div
    ref="entryTop"
    :class="['flex', 'text-lg', {'ml-8': isRead}]">
    <div :class="['flex-shrink-0', 'text-right', 'text-xl']">
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

    <body-list-favicon-column :url="entry.url"/>

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
        @request-to-show-all="entriesStore.displayEntry({entryId: entry.id})"
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
  import {computed, ref, useTemplateRef, onMounted} from "vue";
  import type * as t from "@/logic/types";
  import * as events from "@/logic/events";
import * as e from "@/logic/enums";
  import * as utils from "@/logic/utils";
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
  return utils.purifyTitle({raw: entry.value.title,
                            default_: "No title"});
  });

const purifiedBody = computed(() => {
  return utils.purifyBody({raw: entry.value.body,
                           default_: "No description"});
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
