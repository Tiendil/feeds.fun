<template>
  <div
    v-if="feed !== null"
    class="container">
    <div style="flex-shrink: 0; width: 4rem; left-padding: 0.25rem">
      <a
        href="#"
        @click.prevent="unsubscribe()">
        remove
      </a>
    </div>

    <div
      style="flex-shrink: 0; width: 3rem; left-padding: 0.25rem; cursor: default"
      title="Time of last load">
      <value-date-time
        :value="feed.loadedAt"
        :reversed="true" />
    </div>

    <div
      style="flex-shrink: 0; width: 3rem; left-padding: 0.25rem; cursor: default"
      title="When was added">
      <value-date-time
        :value="feed.linkedAt"
        :reversed="true" />
    </div>

    <div style="flex-shrink: 0; width: 2rem; text-align: right; padding-right: 0.25rem">
      <span
        v-if="feed.isOk"
        title="everything is ok"
        class="state-ok"
        >ok</span
      >
      <span
        v-else
        :title="feed.lastError || 'unknown error'"
        class="state-error"
        >⚠</span
      >
    </div>

    <img :src="faviconUrl" style="width: 1rem; height: 1rem; vertical-align: text-bottom; margin-right: 0.25rem;"/>

  <div style="flex-grow: 1">
      <value-url
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
import * as utils from "@/logic/utils";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

  const properties = defineProps<{feed: t.Feed}>();

const faviconUrl = computed(() => {
  return utils.faviconForUrl(properties.feed.url);
});

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

<style scoped>
  .container {
    display: flex;
  }

  .container :deep(img) {
    max-width: 100%;
    height: auto;
  }

  .state-ok {
    color: green;
    cursor: default;
  }

  .state-error {
    color: red;
    cursor: default;
  }
</style>
