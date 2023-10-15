<template>
  <div
    v-if="feed !== null"
    class="flex mb-1">
    <div class="flex-shrink-0 min-w-fit pr-2">
      <a
        href="#"
        class="ffun-normal-link"
        @click.prevent="unsubscribe()">
        remove
      </a>
    </div>

    <div
      class="flex-shrink-0 w-12 pr-2 text-right cursor-default"
      title="Time of last load">
      <value-date-time
        :value="feed.loadedAt"
        :reversed="true" />
    </div>

    <div
      class="flex-shrink-0 w-12 pr-2 text-right cursor-default"
      title="When was added">
      <value-date-time
        :value="feed.linkedAt"
        :reversed="true" />
    </div>

    <div class="flex-shrink-0 w-8 pr-1 text-right cursor-default">
      <span
        v-if="feed.isOk"
        title="everything is ok"
        class="text-green-700 cursor-default"
        >ok</span
      >
      <span
        v-else
        :title="feed.lastError || 'unknown error'"
        class="text-red-700 cursor-default"
        >⚠</span
      >
    </div>

    <div class="flex-shrink-0 w-8 text-right pr-1">
      <favicon-element
        :url="feed.url"
        class="w-4 h-4 align-text-bottom mx-1 inline" />
    </div>

    <div class="flex-grow">
      <value-url
        class="ffun-normal-link"
        :value="feed.url"
        :text="purifiedTitle" />
      <template v-if="globalSettings.showFeedsDescriptions">
        <br />
        <div v-html="purifiedDescription" />
      </template>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

  const properties = defineProps<{feed: t.Feed}>();

  const purifiedTitle = computed(() => {
    if (properties.feed.title === null) {
      return "";
    }

    let title = DOMPurify.sanitize(properties.feed.title, {ALLOWED_TAGS: []});

    if (title.length === 0) {
      return null;
    }

    return title;
  });

  const purifiedDescription = computed(() => {
    if (properties.feed.description === null) {
      return "";
    }
    return DOMPurify.sanitize(properties.feed.description);
  });

  async function unsubscribe() {
    await api.unsubscribe({feedId: properties.feed.id});
    globalSettings.updateDataVersion();
  }
</script>
